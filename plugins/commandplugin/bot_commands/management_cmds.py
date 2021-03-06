# -*- coding: utf-8 -*-
import traceback

KLASS = 'ManagementCommands'

from bot_command import Command, command_names, admin_only
import sys
from bot_command import MyArgumentParser


class ManagementCommands(Command):
    @command_names(['enable', 'disable'])
    @admin_only
    def enable_disable_plugin(self, command, args, message, plugin):
        return self.enable_plugin(plugin.bot_instance, name=args, enabled=(command == 'enable'))

    def enable_plugin(self, name, enabled=True):
        try:
            self.bot_instance.enable_plugin(name, enabled)
        except KeyError:
            return 'No such plugin: "%s"' % name
        else:
            return ('Enabled' if enabled else 'Disabled') + ' %s' % name

    @command_names('plugins')
    @admin_only
    def list_plugins(self, command, args, message, plugin):
        disabled_str = lambda plug:('' if plug.enabled else ' (disabled)')
        return ', '.join((name + disabled_str(plugin_obj))
                         for name, plugin_obj in self.bot_instance.plugins.iteritems())

    @command_names(['reload', 'reloadall'])
    @admin_only
    def reload_plugins(self, command, args, message, plugin):
        if command == 'reloadall':
            plugin_names = self.bot_instance.plugins.iterkeys()
        else:
            if args not in self.bot_instance.plugins:
                return 'No such plugin: "%s"' % args
            plugin_names = [args]
        self.bot_instance.reload_config()
        for name in plugin_names:
            self.bot_instance.reload_plugin(name)
        return "Reloaded"

    @command_names('reloadconf')
    @admin_only
    def reload_config(self, command, args, message, plugin):
        self.bot_instance.reload_and_apply_config()
        return "Reloaded config"

    exit_parser = MyArgumentParser('exit')
    exit_parser.add_argument('-f', '--force', help='Force exit', action='store_true')
    exit_parser.add_argument('nickname', help='Bot nickname', nargs='?')
    @command_names(['exit'], arg_parser=exit_parser)
    @admin_only
    def bot_exit(self, command, args, message, plugin):
        my_nickname = self.bot_instance.get_my_room_nickname(message.getFrom().getStripped())
        if args.nickname != my_nickname and not args.force:
            return "Type %s %s to %s." % (command, my_nickname, command)
        self.bot_instance.quit()
        sys.exit()

    @command_names(['say', u'скажи'])
    @admin_only
    def say(self, command, args, message, plugin):
        if message.getType() != 'chat':
            return args
        reply_message = message.buildReply(args)
        reply_message.setType('groupchat')
        reply_message.setTo(message.getFrom().getStripped())
        self.bot_instance.send_message(reply_message)

    @command_names(['python'])
    @admin_only
    def exec_python(self, command, args, message, plugin):
        ns = {}
        try:
            exec args in ns
        except Exception, ex:
            return traceback.format_exc()
        if 'result' in ns:
            return str(ns['result'])
        return "Executed"

