#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import functools
import plugins
import shlex
import argparse

def shlex_split(s, comments=False, posix=True):
    ''' Shlex wrapper to add unicode support '''
    is_unicode = False
    if isinstance(s, unicode):
        s = s.encode('utf-8')
        is_unicode = True
    result = shlex.split(s, comments=comments, posix=posix)
    if is_unicode:
        result = [arg.decode('utf-8') for arg in result]
    return result

class ExitException(Exception):
    ''' Raised by MyArgumentParser instead of sys.exit() and writing to stderr '''

class MyArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        pass

    def _print_message(self, message, file=None):
        raise ExitException(message)


COMMAND_METHOD_ATTR = '_method_commands'
IS_RETURNED_BY_EXEC_TASK_ATTR = '_is_returned_by_exec_task'

def _add_command_handler(command, method, dct):
    conflicting_method = dct.get(command, None)
    if conflicting_method is not None:
        raise CommandConflict(command, method, conflicting_method)
    dct[command] = method

def command_names(names, arg_parser=None):
    ''' This decorates all functions that will be registered as commands. 
    names is a list of command names '''
    if isinstance(names, basestring):
        names = [names]
    def decorator(func, add_command_attr=True):
        if add_command_attr:
            setattr(func, COMMAND_METHOD_ATTR, names)
        @functools.wraps(func)
        def wrapper(self, command, args, message, plugin):
            error_happened = False
            if arg_parser is not None:
                try:
                    args = arg_parser.parse_args(shlex_split(args))
                except Exception, ex:
                    result = ex.args[0].strip()
                    error_happened = True
            if not error_happened:
                try:
                    result = func(self, command, args, message, plugin)
                except Exception, ex:
                    result = '%s exception happened while executing "%s" with args "%s", traceback saved into error log.' % (ex.__class__.__name__, command, args)
                    plugin.logger.error("While executing command '%s' with args '%s'", command, args, exc_info=True)
                    error_happened = True
            if isinstance(result, basestring):
                plugin.send_simple_reply(message, result, include_nick=error_happened)
            elif isinstance(result, plugins.ThreadedPluginTask):
                if getattr(result, IS_RETURNED_BY_EXEC_TASK_ATTR, False):
                    result.function_to_execute = decorator(result.function_to_execute, add_command_attr=False)
                if not plugin.add_task(result):
                    plugin.send_simple_reply("Failed to add your task to queue because of limitations.", include_nick=True)
        return wrapper
    return decorator

def exec_as_task(func):
    @functools.wraps(func)
    def wrapper(self, command, args, message, plugin):
        task = plugins.ThreadedPluginTask(plugin, func, self, command, args, message, plugin)
        setattr(task, IS_RETURNED_BY_EXEC_TASK_ATTR, True)
        return task
    return wrapper

class CommandConflict(Exception):
    ''' This exception is raised when two methods share same command name '''
    def __init__(self, name, method1, method2):
        super(CommandConflict, self).__init__()
        self.name, self.method1, self.method2 = name, method1, method2

    def __str__(self):
        return ("For command '%s', methods: %r and %r" %
                (self.name, self.method1, self.method2))

def admin_only(func):
    @functools.wraps(func)
    def wrapper(self, command, args, message, plugin):
        if not self._is_from_admin(plugin.bot_instance, message):
            return "Sorry, you don't have enough privileges to execute '%s' command." % command
        return func(self, command, args, message, plugin)
    return wrapper

class Command(plugins.bot_module.BotModule):
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

    admins = plugins.make_config_property('admins', default=lambda:[])

    def __init__(self, config_section, logger=None):
        super(Command, self).__init__(config_section, logger=logger)

    def get_registered_commands(self):
        result = {}
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, method in methods:
            command_names = getattr(method, COMMAND_METHOD_ATTR, [])
            for command_name in command_names:
                _add_command_handler(command_name, method, result)
        return result

    def _is_from_admin(self, bot_instance, message):
        return bot_instance.is_from_admin(message)

