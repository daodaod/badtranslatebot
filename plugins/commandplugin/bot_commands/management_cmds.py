'''
Created on 08.08.2013

@author: H
'''
import plugins
from bot_command import Command, command_names, admin_only

class ManagementCommands(Command):
    admins = plugins.make_config_property('admins', default=[])

    @admin_only
    @command_names('enable', 'disable')
    def enable_disable(self, command, args, bot_instance, **kwargs):
        return self.enable_plugin(bot_instance, args, enabled=(command == 'enable'))

    def enable_plugin(self, bot_instance, name, enabled=True):
        try:
            bot_instance.enable_plugin(name, enabled)
        except KeyError:
            return 'No such plugin: "%s"' % name
        else:
            return ('Enabled' if enabled else 'Disabled') + ' %s' % name

    @admin_only
    @command_names('plugins')
    def list_plugins(self, command, args, bot_instance, **kwargs):
        disabled_str = lambda plug:('' if plug.enabled else ' (disabled)')
        return ', '.join((name + disabled_str(plugin))
                         for name, plugin in bot_instance.plugins.iteritems())

    @admin_only
    @command_names('reload', 'reloadall')
    def reload_plugins(self, command, args, bot_instance, **kwargs):
        if command == 'realodall':
            plugin_names = bot_instance.plugins.iterkeys()
        else:
            if args not in bot_instance.plugins:
                return 'No such plugin: "%s"' % args
            plugin_names = [args]
        bot_instance.reload_config()
        for name in plugin_names:
            bot_instance.reload_plugin(name)

    @admin_only
    @command_names('reloadconf')
    def reload_config(self, command, args, bot_instance, **kwargs):
        bot_instance.reload_and_apply_config()

    def _is_from_admin(self, bot_instance, message):
        if super(ManagementCommands, self)._is_from_admin(bot_instance, message):
            return True
        if message.getFrom().getStripped() in self.admins:
            return True
        if message.getType() == 'groupchat':
            user = bot_instance.get_room_user_by_jid(message.getFrom())
            return user.jid.partition('/')[0] in self.admins
        return False
