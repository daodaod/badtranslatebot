#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins


class ChatlogPlugin(method_plugins.JabberPlugin):
    @plugins.register_plugin_method
    def process_message(self, message):
        print "Logging message!"
        print message
        
    @plugins.register_plugin_method
    def process_presence(self, presence):
        print "Logging presence!"
        print presence
        
        
if __name__ == '__main__':
    pass