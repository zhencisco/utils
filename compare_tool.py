#!/usr/bin/env python

import os, argparse, logging, difflib, prettytable, textwrap

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('debug.log')
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

class CompareTool(object):
    NEW = 'new'
    DELETED = 'removed'
    UPDATED = 'updated'
    FIELDNAME = ['status', 'option', 'value(Icehouse)', 'value(Liberty)']
    VALID_CONFIG_EXTS = ['ini', 'conf']

    def __init__(self, path1, path2, wrap, is_markup, sortby_field):
        self.markup = is_markup
        if self.markup:
            self.wrap = 0
        else:
            self.wrap = wrap
        self.sortby_field = sortby_field
        self.tableDict = dict()
        self.section = ''
        fileDict1 = self.feed_files(path1)
        fileDict2 = self.feed_files(path2)
        fileList = fileDict1.keys()
        for file in fileList:
            file1 = fileDict1.get(file, None)
            file2 = fileDict2.get(file, None)
            self.filename = file
            if file1 and file2:
                self.compare(file1, file2)
            else:
                print "The peer file of %s doesn't exist, pass!" % (file1 or 
                        file2)
        self.print_table()

    # assume the files to be compared have same file name but are in different directories
    def feed_files(self, path):
        fileDict = dict()
        for root, dirs, files in os.walk(os.path.join(path)):
            for file_name in files:
                ext = os.path.splitext(file_name)[1]
                if ext and ext[1:] in self.VALID_CONFIG_EXTS:
                    filePath = os.path.join(root, file_name)
                    fileDict[file_name] = filePath
        return fileDict

    def compare(self, filePath1, filePath2):
        with open(filePath1, "rU") as file1, open(filePath2, "rU") as file2:
            file1Lines = file1.read().splitlines(1)
            file2Lines = file2.read().splitlines(1)
        diffResult = list(difflib.unified_diff(file1Lines, file2Lines, 
                            n=100000))
        logger.debug(filePath1)
        logger.debug(filePath2)
        for line in diffResult:
            logger.debug(line)
        length = len(diffResult)
        i = 0
        while i < length:
            line = diffResult[i].strip()
            if len(line) <= 1:
                line = None
            if i + 1 < length:
                nextLine = diffResult[i+1].strip()
                if len(nextLine) <= 1:
                    nextLine = None
            else:
                nextLine = None
            i += 1

            if line and (line[0] == '[' or line[1] == '['):
                self.section = line.strip()
            elif line and line[0] == '-' and line[1] != '-':
                elements = self.split_line(line)
                if nextLine and nextLine[0] == '+' and nextLine[1] != '[':
                    nextElements = self.split_line(nextLine)
                    # the option exists in both icehouse and liberty config file but its value is updated.
                    if elements[0] == nextElements[0]:
                        elements.insert(0, self.UPDATED)
                        elements.append(nextElements[1])
                        self.make_table(elements)
                    else:
                        # for the line, the option only exists in icehouse config file.
                        elements.insert(0, self.DELETED)
                        elements.append('')
                        # for the next line, the option only exists in liberty config file.
                        nextElements.insert(1, '')
                        nextElements.insert(0, self.NEW)
                        self.make_table(elements)
                        self.make_table(nextElements)
                    i += 1
                else:
                    # the option only exists in icehouse config file.
                    elements.insert(0, self.DELETED)
                    elements.append('')
                    self.make_table(elements)
            # the option only exists in liberty config file.
            elif line and line[0] == '+' and line[1] != '+':
                elements = self.split_line(line)
                elements.insert(1, '')
                elements.insert(0, self.NEW)
                self.make_table(elements)

    def split_line(self, line):
        elements = line[1:].split('=', 1)
        elements = map(str.strip, elements)
        return elements

    def make_table(self, elements):
        elements = map(self.wrap_line, elements)
        if self.markup:
            elements = map(self.replace_square_brackets, elements)
        if self.tableDict.has_key(self.filename):
            if self.tableDict[self.filename].has_key(self.section):
                # add row to existing table
                table = self.tableDict[self.filename][self.section]
            else:
                # create a new table for existing file
                table = prettytable.PrettyTable()
                table.field_names = self.FIELDNAME
                self.tableDict[self.filename][self.section] = table
        else:
            # create a new table for new file
            table = prettytable.PrettyTable()
            table.field_names = self.FIELDNAME
            self.tableDict[self.filename] = {self.section: table}
        table.add_row(elements)

    def wrap_line(self, v):
        if self.wrap > 0:
            v = textwrap.fill(v, self.wrap)
        return v

    def replace_square_brackets(self, v):
        v = v.replace('[', '\[')
        v = v.replace(']', '\]')
        return v

    def print_table(self):
        for file in self.tableDict:
            if self.markup:
                breaker = '\\\\'
                print "h2.*" + file + "*"
                print breaker + ' ' + breaker
            else:
                breaker = ''
                fileTitle = "*" + file + "*"
                length = len(fileTitle)
                print '\n\n'+'=' * length
                print "*" + file + "*"
                print '=' * length + '\n'
            keys = self.tableDict[file].keys()
            keys.sort(key=lambda x: x.translate(None, '+-'))
            for section in keys:
                if section[0] == '-':
                    sectionDesc = section[1:] + '(deleted)'
                elif section[0] == '+':
                    sectionDesc = section[1:] + '(added)'
                else:
                    sectionDesc = section
                table = self.tableDict[file][section]
                if self.markup:
                    sectionDesc = self.replace_square_brackets(sectionDesc)
                    print '*%s: %s*' % (file, sectionDesc)
                    print breaker
                    print "||" + "||".join(self.FIELDNAME)  + "||"
                    table.header = False
                    table.hrules = prettytable.NONE
                else:
                    print '*%s: %s*' % (file, sectionDesc)
                    table.align = 'l'
                print table.get_string(sortby=self.sortby_field)
                print breaker
            print breaker + ' ' + breaker

def main():
    usage = "usage: %prog [options] ICEHOUSE_DIR LIBERTY_DIR"
    desc = 'Compare the configuration files generated from Icehouse and \
            Liberty.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('dir1', metavar='ICEHOUSE_DIR',
                        help='directory of config files of Icehouse')
    parser.add_argument('dir2', metavar='LIBERTY_DIR',
                        help='directory of config files of Liberty')
    parser.add_argument("-w", "--wrap", metavar='NUM', type=int, default=90,
                        help="the width of the columns, the default value is \
                        90, set 0 to turn off wrapping.")
    parser.add_argument("-m", "--markup", action="store_true",
                        help="output Confluence wiki markup, '-wrap' setting \
                        will be ignored in this case.")
    parser.add_argument("-s", "--sortby", default="option", 
                        choices=["status", "option"], 
                        help="sort the data by the field 'option'(default) or \
                            'status'.")
    args = parser.parse_args()
    dir1 = args.dir1
    dir2 = args.dir2
    wrap = args.wrap
    is_markup = args.markup
    sortby_field = args.sortby
    CompareTool(dir1, dir2, wrap, is_markup, sortby_field)

if __name__ == '__main__':
    main()