#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import logging
import plugins.bot_module
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

def is_registered_method(fn):
    return bool(getattr(fn, PLUGIN_METHOD_ATTR, False))

class JabberPlugin(plugins.bot_module.BotModule):
    ''' This class is base for all plugins '''
    # If set to True, plugin will handle stanzas even if another handler has raised StanzaProcessed.
    # This allows us to implement logging/stats plugins that log everythin with minor changes.
    always_handle = False

    def __init__(self, config_section, logger=None):
        super(JabberPlugin, self).__init__(config_section, logger=logger)
        self.enabled = True

    def enable(self, enabled=True):
        self.enabled = enabled

    def get_registered_methods_names(self):
        ''' Returns list of method's names for which `register_plugin_method` was called. '''
        result = []
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, method in methods:
            if getattr(method, PLUGIN_METHOD_ATTR, False):
                result.append(name)
        return result

    # Shortcuts
    send_simple_reply = property(lambda self:self.bot_instance.send_simple_reply)


if __name__ == '__main__':
    from plugins.bot_module import make_config_property
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
