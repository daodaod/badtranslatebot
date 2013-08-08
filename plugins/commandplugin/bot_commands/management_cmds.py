'''
Created on 08.08.2013

@author: H
'''
import plugins
from bot_command import Command, command_names, admin_only

class ManagementCommands(Command):
    admins = plugins.make_config_property('admins', default=[])

    @admin_only
    @command_names('enable')
    def enable(self, command, args, bot_instance, **kwargs):
        print self.admins
        return self.enable_plugin(bot_instance, args, enabled=True)

    @admin_only
    @command_names('disable')
    def disable(self, command, args, bot_instance, **kwargs):
        return self.enable_plugin(bot_instance, args, enabled=False)

    def enable_plugin(self, bot_instance, name, enabled=True):
        try:
            bot_instance.enable_plugin(name)
        except KeyError:
            return 'No such plugin: "%s"' % name
        else:
            return ('Enabled' if enabled else 'Disabled') + ' %s' % name

    def _is_from_admin(self, bot_instance, message):
        if super(ManagementCommands, self)._is_from_admin(bot_instance, message):
            return True
        if message.getFrom().getStripped() in self.admins:
            return True
        if message.getType() == 'groupchat':
            user = bot_instance.get_room_user_by_jid(message.getFrom())
            return user.jid.partition('/')[0] in self.admins
        return False
