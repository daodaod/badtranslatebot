#!/usr/bin/env python
# -*- coding: utf-8 -*-

import persistentbot
import threadpool
import traceback
import importlib
import collections
# ##
import plugins
import plugins.commandplugin
import plugins.commandplugin.bot_commands.management_cmds

import logging

# TODO: How about help?
# TODO: How about comments in config?
# TODO: Think about django-style plugin reloading (this would allow inheritance for example)

class ExtendableJabberBot(persistentbot.PersistentJabberBot):
    def __init__(self, username, password, config, logger=None, res=None, debug=False,
        privatedomain=False, acceptownmsgs=False):
        super(ExtendableJabberBot, self).__init__(username, password, res=res, debug=debug, privatedomain=privatedomain, acceptownmsgs=acceptownmsgs)
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self.plugins = collections.OrderedDict()  # plugin name -> plugin
        self.commands = collections.OrderedDict()  # command name -> command
        self.threadpool = threadpool.TaskPool(exception_handler=self.threadpool_exc_handler)
        self.apply_config(load_plugins=True, load_commands=True)
        management_config = config['management']
        management_plugin = plugins.commandplugin.CommandPlugin(management_config)
        management_plugin.add_bot_instance(self)
        management_command = plugins.commandplugin.bot_commands.management_cmds.ManagementCommands(management_config)
        # TODO: How do we fix this? It looks ugly!
        management_command.add_bot_instance(self)
        management_plugin.register_command(management_command)
        self.compulsory_plugins = [("management", management_plugin)]

    def threadpool_exc_handler(self, etype, value, tb):
        try:
            raise etype, value, tb
        except etype:
            self.logger.error("Exception happened while serving threadpool task", exc_info=1)

    def serve_exc_handler(self, etype, value, tb):
        try:
            raise etype, value, tb
        except etype:
            self.logger.error("Exception happened while serve forever", exc_info=1)


    def handle_plugins(self, methodname, *args, **kwargs):
        to_process = [self.compulsory_plugins, self.plugins.iteritems()]
        stanza_processed = False
        for plugin_items in to_process:
            for name, plugin in plugin_items:
                if not plugin.enabled or (stanza_processed and not plugin.always_handle):
                    continue
                try:
                    self.handle_plugin_method(name, plugin, methodname, *args, **kwargs)
                except plugins.StanzaProcessed:
                    stanza_processed = True

    def handle_plugin_method(self, name, plugin, methodname, *args, **kwargs):
        func = getattr(plugin, methodname, None)
        if func is None or (not plugins.is_registered_method(func)):
            return
        try:
            func(*args, **kwargs)
        except plugins.StanzaProcessed:
            raise
        except Exception:
            self.logger.error("Exception happened while serving plugin method %s of plugin %s" % (methodname, name),
                              exc_info=1)

    def register_module(self, module, name, modules_dict, re_register=False):
        ''' Registers plugin in our bot. If that plugin instance is already registered, do nothing.
        Warning! Order in which you register plugins matters. Plugin methods will be called directly in that
        order. So, the most important plugins e.g. logging should be registered first since other plugins
        may stop processing cycle by raising StanzaProcessed exception.
        If name is None, '''
        if name in modules_dict and not re_register:
            return False
        if not module.add_bot_instance(self):
            return False
        modules_dict[name] = module
        return True

    def unregister_module(self, name, modules_dict):
        ''' Unregisters plugin from our bot. Raises ValueError if plugin was not registered previously '''
        module = modules_dict[name]
        module.shutdown()
        module.remove_bot_instance(self)
        modules_dict.pop(name)

    def reload_config(self):
        self.config.reload()

    def reload_and_apply_config(self):
        self.config.reload()
        self.apply_config()

    def load_module_class(self, module_name, reload_module=False):
        module = importlib.import_module(module_name)
        if reload_module:
            reload(module)
        module_cls = getattr(module, module.KLASS)
        return module_cls

    def load_module(self, module_config, reload_module=False):
        module_cls = self.load_module_class(module_config['module'], reload_module=reload_module)
        return module_cls(module_config['config'])

    def reload_module(self, name, modules_dict, module_config):
        old_module = modules_dict[name]
        module = self.load_module(module_config, reload_module=True)
        self.register_module(module, name, modules_dict, re_register=True)
        old_module.shutdown()

    def reload_plugin(self, name):
        plugin_config = self.config['plugins'][name]
        self.reload_module(name, self.plugins, plugin_config)

    def enable_plugin(self, name, enabled=True):
        self.enable_module(name, self.plugins, enabled)

    def enable_module(self, name, modules_dict, enabled=True):
        module = modules_dict[name]
        module.enable(enabled)

    def apply_config(self, load_plugins=False, load_commands=False):
        ''' Applies config to bot, if load_plugins is True, it loads plugins that aren't loaded yet '''
        # rooms
        rooms_config = self.config['rooms']
        for name, room in rooms_config.iteritems():
            self.add_room(room['jid'], room['nickname'], room.get('password'))
        # commands, general options
        commands_config = self.config.get('commands')
        if commands_config:
            # commands
            self.apply_modules_config(commands_config, self.commands, load_commands)
        # plugins general options
        plugins_config = self.config.get('plugins')
        if plugins_config:
            workers_num = plugins_config.as_int('pool_workers')
            self.threadpool.resize_workers(workers_num)
            # plugins
            self.apply_modules_config(plugins_config, self.plugins, load_plugins)

    def apply_modules_config(self, modules_config, modules_dict, load_modules=False):
        ''' This routine only applies configuration from configobj to existing plugins. It doesn't load/unload/reload plugins. '''
        for module_name in modules_config.sections:
            module_config = modules_config[module_name]
            if module_name in modules_dict:
                module = modules_dict[module_name]
                module.apply_config(module_config['config'])
            elif load_modules:
                module = self.load_module(module_config)
                self.register_module(module, module_name, modules_dict)

    def process_message(self, message):
        self.handle_plugins(self.process_message.__name__, message)

    def process_message_error(self, message):
        self.handle_plugins(self.process_message_error.__name__, message)

    def process_delayed_message(self, message):
        self.handle_plugins(self.process_delayed_message.__name__, message)

    def process_text_message(self, message, **kwargs):
        # self.reload_and_apply_config()
        self.handle_plugins(self.process_text_message.__name__, message, **kwargs)

    def process_presence(self, presence):
        self.handle_plugins(self.process_presence.__name__, presence)

    def idle_proc(self):
        super(ExtendableJabberBot, self).idle_proc()
        for plugin_name, plugin in self.plugins.iteritems():
            plugin.idle_proc()
        for command_name, command in self.commands.iteritems():
            command.idle_proc()

    def is_from_admin(self, message):
        room_user = self.get_room_user_by_jid(message.getFrom())
        admins = self.config['management']['admins']
        if message.getType() == 'chat' and room_user is None:
            return message.getFrom().getStripped() in admins
        else:
            if room_user is None:
                return False
            if room_user.affiliation in self.config['management']['allowed_affiliations']:
                return True
            return room_user.jid and room_user.jid.partition('/')[0] in admins

if __name__ == '__main__':
    import configobj
    import argparse
    import logging.config
    import os
    import StringIO
    DEBUG = os.path.exists('debug.config')
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Configuration file with bot and plugin settings")
    parser.add_argument("--configspec", help="Configuration specification file used when loading config file",
                        default='config/config.spec')
    parser.add_argument("--logconfig", help="Logging config file",
                        default='config/logging.conf')
    if DEBUG:
        namespace = parser.parse_args(['config/alice.config'])
    else:
        namespace = parser.parse_args()
    config = configobj.ConfigObj(namespace.config, encoding='utf-8')
    acc_info = config['jabber_account']
    login = acc_info['jid']
    password = acc_info['password']
    resource = acc_info.get('resource', None)
    logging_folder = config['logging']['folder']
    if not os.path.exists(logging_folder):
        os.makedirs(logging_folder)
    with open(namespace.logconfig, "rb") as f:
        data = f.read().replace("{{LOG_DIRECTORY}}", logging_folder)
    buf = StringIO.StringIO(data)
    logging.config.fileConfig(buf, disable_existing_loggers=False)
    bot = ExtendableJabberBot(login, password, config, res=resource)

    bot.serve_really_forever(bot.serve_exc_handler)
