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
        commutated = self.chatvdvoem_plugin.commutated
        if not commutated:
            return u"Я не связан ни с кем"
        return u"Я связан с " + ','.join(self.chatvdvoem_plugin.commutated)

    kill_parser = MyArgumentParser('kill')
    kill_parser.add_argument('-s', '--stop', action='store_true', help='Set non-stop to false')

    @command_names(['kill', u'отключи', u'отключись', u'уходи'], arg_parser=kill_parser)
    def kill(self, command, args, message, plugin):
        if args.stop:
            self.set_nonstop(False)
        self.chatvdvoem_plugin.kill_chatvdvoem()
        return "Killed" + (' and stopped' if args.stop else '')

    def set_nonstop(self, non_stop):
        self.chatvdvoem_plugin.non_stop = non_stop

    nonstop_parser = MyArgumentParser('nonstop')
    nonstop_parser.add_argument('state', choices=['on', 'off'], nargs='?', default='on')
    @command_names(['nonstop', u'нонстоп'], arg_parser=nonstop_parser)
    def nonstop(self, command, args, message, plugin):
        non_stop = (args.state == 'on')
        self.set_nonstop(non_stop)
        return "Non-stop is %r" % non_stop
