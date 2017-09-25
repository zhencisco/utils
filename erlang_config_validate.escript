#!/usr/bin/env escript

% Validate the config file used by Erlang 

main([ConfigFile]) ->
    {ok, Terms} = file:consult(ConfigFile),
    io:format("~p~n",[Terms]).
