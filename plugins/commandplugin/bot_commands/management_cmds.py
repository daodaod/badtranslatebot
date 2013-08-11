'''
Created on 08.08.2013

@author: H
'''
import plugins
from bot_command import Command, command_names, admin_only, exec_as_task

class ManagementCommands(Command):
    @command_names('enable', 'disable')
    @admin_only
    def enable_disable_plugin(self, command, args, message, plugin):
        return self.enable_plugin(plugin.bot_instance, name=args, enabled=(command == 'enable'))

    def enable_plugin(self, bot_instance, name, enabled=True):
        try:
            bot_instance.enable_plugin(name, enabled)
        except KeyError:
            return 'No such plugin: "%s"' % name
        else:
            return ('Enabled' if enabled else 'Disabled') + ' %s' % name

    @command_names('plugins')
    @admin_only
    @exec_as_task
    def list_plugins(self, command, args, message, plugin):
        disabled_str = lambda plug:('' if plug.enabled else ' (disabled)')
        return ', '.join((name + disabled_str(plugin_obj))
                         for name, plugin_obj in plugin.bot_instance.plugins.iteritems())

    @command_names('reload', 'reloadall')
    @admin_only
    def reload_plugins(self, command, args, message, plugin):
        if command == 'realodall':
            plugin_names = plugin.bot_instance.plugins.iterkeys()
        else:
            if args not in plugin.bot_instance.plugins:
                return 'No such plugin: "%s"' % args
            plugin_names = [args]
        plugin.bot_instance.reload_config()
        for name in plugin_names:
            plugin.bot_instance.reload_plugin(name)

    @command_names('reloadconf')
    @admin_only
    def reload_config(self, command, args, message, plugin):
        plugin.bot_instance.reload_and_apply_config()
