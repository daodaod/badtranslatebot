#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect

PLUGIN_METHOD_ATTR = '_plugin_method'

def register_plugin_method(fn):
    ''' Methods decorated will be called from `handle_plugins` of persistentbot.
    Note, that those methods will receive bot_instance parameter referencing to
    PersistentBot instance.'''
    setattr(fn, PLUGIN_METHOD_ATTR, True)
    return fn

class JabberPlugin(object):
    ''' This class is base for all plugins '''
    
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
            
    t = TestPlugin()
    print t.get_registered_methods_names()