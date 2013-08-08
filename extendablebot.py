#!/usr/bin/env python
# -*- coding: utf-8 -*-

import persistentbot
import threadpool
import traceback
import importlib
# ##
import plugins
import plugins.commandplugin
import plugins.commandplugin.bot_commands.management_cmds

class ExtendableJabberBot(persistentbot.PersistentJabberBot):
    def __init__(self, username, password, config, res=None, debug=False,
        privatedomain=False, acceptownmsgs=False):
        self.config = config
        self.method_plugins = {}  # method name -> [list of plugins]
        self.plugins = {}  # plugin name -> plugin
        self.threadpool = threadpool.TaskPool(exception_handler=self.threadpool_exc_handler)
        super(ExtendableJabberBot, self).__init__(username, password, res=res, debug=debug, privatedomain=privatedomain, acceptownmsgs=acceptownmsgs)
        self.apply_config(load_plugins=True)
        management_config = config['management']
        management_plugin = plugins.commandplugin.CommandPlugin(management_config)
        management_command = plugins.commandplugin.bot_commands.management_cmds.ManagementCommands(management_config)
        management_plugin.register_command(management_command)
        self.register_plugin(management_plugin)

    def threadpool_exc_handler(self, etype, value, tb):
        traceback.print_exception(etype, value, tb)

    def handle_plugins(self, methodname, *args, **kwargs):
        for plugin in self.method_plugins.get(methodname, []):
            func = getattr(plugin, methodname)
            kwargs['bot_instance'] = self
            try:
                func(*args, **kwargs)
            except plugins.StanzaProcessed:
                break  # TODO: Maybe add logging.log here?

    def register_plugin(self, plugin):
        ''' Registers plugin in our bot. If that plugin instance is already registered, do nothing.
        Warning! Order in which you register plugins matters. Plugin methods will be called directly in that
        order. So, the most important plugins e.g. logging should be registered first since other plugins
        may stop processing cycle by raising StanzaProcessed exception.
        If name is None, '''
        if not plugin.add_bot_instance(self):
            return False
        for methodname in plugin.get_registered_methods_names():
            plugins_list = self.method_plugins.setdefault(methodname, [])
            plugins_list.append(plugin)
        return True

    def register_named_plugin(self, plugin, name):
        if name in self.plugins:
            return False
        if not self.register_plugin(plugin):
            return False
        self.plugins[name] = plugin
        return True

    def unregister_plugin(self, plugin):
        ''' Unregisters plugin from our bot. Raises ValueError if plugin was not registered previously '''
        plugin.remove_bot_instance(self)
        for methodname in plugin.get_registered_methods_names():
            plugins_list = self.method_plugins[methodname]
            plugins_list.remove(plugin)
            if not plugins_list:
                self.method_plugins.pop(methodname)

    def unregister_named_plugin(self, name):
        plugin = self.plugins[name]
        self.unregister_plugin(plugin)
        self.names.pop(name)

    def reload_and_apply_config(self):
        self.config.reload()
        self.apply_config()

    def load_plugin(self, plugin_config):
        module_name = plugin_config['module']
        module = importlib.import_module(module_name)
        plugin_cls = getattr(module, module.PLUGIN_CLASS)
        return plugin_cls(plugin_config['config'])

    def enable_plugin(self, name, enabled=True):
        plugin = self.plugins[name]
        plugin.enable(enabled)

    def apply_config(self, load_plugins=False):
        ''' Applies config to bot, if load_plugins is True, it loads plugins that aren't loaded yet '''
        # rooms
        rooms_config = self.config['rooms']
        for name, room in rooms_config.iteritems():
            self.add_room(room['jid'], room['nickname'], room.get('password'))
        # plugins general options
        plugins_config = self.config['plugins']
        workers_num = plugins_config.as_int('pool_workers')
        self.threadpool.resize_workers(workers_num)
        # plugins
        self.apply_plugins_config(plugins_config, load_plugins)

    def apply_plugins_config(self, plugins_config, load_plugins=False):
        ''' This routine only applies configuration from configobj to existing plugins. It doesn't load/unload/reload plugins. '''
        for plugin_name in plugins_config.sections:
            plugin_config = plugins_config[plugin_name]
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                plugin.apply_config(plugin_config['config'])
            elif load_plugins:
                plugin = self.load_plugin(plugin_config)
                self.register_named_plugin(plugin, plugin_name)

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

if __name__ == '__main__':
    DEBUG = True
    import configobj
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Configuration file with bot and plugin settings")
    if DEBUG:
        namespace = parser.parse_args(['config/john.config'])
    else:
        namespace = parser.parse_args()
    config = configobj.ConfigObj(namespace.config)
    acc_info = config['jabber_account']
    login = acc_info['jid']
    password = acc_info['password']
    resource = acc_info.get('resource', None)

    bot = ExtendableJabberBot(login, password, config, res=resource)

    bot.serve_really_forever(traceback.print_exception)

