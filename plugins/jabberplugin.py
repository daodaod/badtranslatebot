#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect

PLUGIN_METHOD_ATTR = '_plugin_method'

class StanzaProcessed(Exception):
    ''' Plugin method may raise this exception if it thinks that stanza concerns only
     this plugin and no further plugins should process this stanza '''
    pass

def register_plugin_method(fn):
    ''' Methods decorated will be called from `handle_plugins` of persistentbot.
    Note, that those methods will receive bot_instance parameter referencing to
    PersistentBot instance.'''
    setattr(fn, PLUGIN_METHOD_ATTR, True)
    return fn
__sentinel = object()
def make_config_property(field, getter=None, setter=None, default=__sentinel):
    def fget(self):
        if default != __sentinel:
            value = self.config_section.get(field, default)
        else:
            value = self.config_section[field]
        if getter is not None: value = getter(value)
        return value
    def fset(self, value):
        if setter is not None:
            value = setter(value)
        self.config_section[field] = value
    return property(fget, fset)

class JabberPlugin(object):
    ''' This class is base for all plugins '''

    def __init__(self, config_section):
        self.apply_config(config_section)
        self.bot_instances = []
        self.enabled = True

    def enable(self, enabled=True):
        self.enabled = enabled

    def add_bot_instance(self, bot_instance):
        if bot_instance in self.bot_instances:
            return False
        self.bot_instances.append(bot_instance)
        return True

    def apply_config(self, config_section):
        self.config_section = config_section

    def remove_bot_instance(self, bot_instance):
        self.bot_instances.remove(bot_instance)

    def get_registered_methods_names(self):
        ''' Returns list of method's names for which `register_plugin_method` was called. '''
        result = []
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, method in methods:
            if getattr(method, PLUGIN_METHOD_ATTR, False):
                result.append(name)
        return result


if __name__ == '__main__':
    class TestPlugin(JabberPlugin):
        @register_plugin_method
        def process_message(self, mess, bot_instance):
            print mess

        foo = make_config_property('foo', int, str)
    conf = {'foo': '9'}
    t = TestPlugin(conf)
    print t.get_registered_methods_names()
    print t.foo
    t.foo = 99
    print conf
