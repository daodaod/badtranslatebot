#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
from bot_command import Command, command_names, admin_only, exec_as_task
from plugins.bot_module import make_config_property

KLASS = 'ChatvdvoemCommands'

class ChatvdvoemCommands(Command):
    chatvdvoem_plugin = make_config_property('chatvdvoem_plugin',
                                             getter=lambda self, name:self.bot_instance.plugins.get(name))

    @command_names(u'commutate', u'соедини', u'коммутируй')
    def commutate(self, command, args, message, plugin):
        print self.chatvdvoem_plugin
        return u"Hey ho!"
