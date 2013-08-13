#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
from bot_command import Command, command_names, admin_only, exec_as_task, MyArgumentParser
from plugins.bot_module import make_config_property

KLASS = 'ChatvdvoemCommands'

class ChatvdvoemCommands(Command):
    chatvdvoem_plugin = make_config_property('chatvdvoem_plugin',
                                             getter=lambda self, name:self.bot_instance.plugins.get(name))

    commutate_parser = MyArgumentParser('commutate')
    commutate_parser.add_argument('-b', '--break', action='store_true', default=False,
                                  help='Removes nickname from commutated list', dest='break_conn')
    commutate_parser.add_argument('nickname')
    @command_names([u'commutate', u'свяжи', u'свяжись', u'отвяжись', u'отвяжи'], arg_parser=commutate_parser)
    def commutate(self, command, args, message, plugin):
        if command in [u'отвяжись', u'отвяжи']:
            args.break_conn = True
        if args.break_conn:
            self.chatvdvoem_plugin.commutated.discard(args.nickname)
        else:
            user = self.bot_instance.get_room_user(message.getFrom().getStripped(), args.nickname)
            if user is None:
                return "No such nickname!"
            self.chatvdvoem_plugin.commutated.add(args.nickname)
        return "Ok"

    @command_names([u'commutation', u'связи'])
    def commutation(self, command, args, message, plugin):
        return ','.join(self.chatvdvoem_plugin.commutated)
