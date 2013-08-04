#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect

COMMAND_METHOD_ATTR = '_method_commands'

def _add_command_handler(command, method, dct):
    conflicting_method = dct.get(command, None)
    if conflicting_method is not None:
        raise CommandConflict(command, method, conflicting_method)
    dct[command] = method

def command_names(*names):
    ''' This decorates all functions that will be registered as commands. 
    names is a list of command names '''

    def decorator(func):
        setattr(func, COMMAND_METHOD_ATTR, names)
        return func
    return decorator

class CommandConflict(Exception):
    ''' This exception is raised when two methods share same command name '''
    def __init__(self, name, method1, method2):
        super(CommandConflict, self).__init__()
        self.name, self.method1, self.method2 = name, method1, method2

    def __str__(self):
        return ("For command '%s', methods: %r and %r" %
                (self.name, self.method1, self.method2))

class Command(object):
    ''' This class is base for all bot commands 
    
    Example command:

    @command('hello', 'hi')
    def say_hello(self, command, args, message, plugin, bot_instance):
        return 'Hey!'
        
    or for those, who needn't all that additional params
        
    @command('hello', 'hi')
    def say_hello(self, command, args, **kwargs):
        return 'Hey!'
        
    If the return value is string, it will be replied to sender. 
    If instead it's a task, it will be executed in a thread pool (or not, if pool queue is full)
    so if you want reliability, you should add it yourself and return None instead.
    
    If return value is None, nothing is done '''

    def get_registered_commands(self):
        result = {}
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, method in methods:
            command_names = getattr(method, COMMAND_METHOD_ATTR, [])
            for command_name in command_names:
                _add_command_handler(command_name, method, result)
        return result
