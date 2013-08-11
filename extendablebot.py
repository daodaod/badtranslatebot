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

# TODO: Add exception handler to plugin handler
# TODO: Add logging (+ config it)
# TODO: How about allowing to change and save plugin configuration?
# TODO: How about help?
# TODO: How about comments in config?
# TODO: Think about django-style plugin reloading (this would allow inheritance for example)

class ExtendableJabberBot(persistentbot.PersistentJabberBot):
    def __init__(self, username, password, config, res=None, debug=False,
        privatedomain=False, acceptownmsgs=False):
        self.config = config
        self.plugins = collections.OrderedDict()  # plugin name -> plugin
        self.threadpool = threadpool.TaskPool(exception_handler=self.threadpool_exc_handler)
        super(ExtendableJabberBot, self).__init__(username, password, res=res, debug=debug, privatedomain=privatedomain, acceptownmsgs=acceptownmsgs)
        self.apply_config(load_plugins=True)
        management_config = config['management']
        management_plugin = plugins.commandplugin.CommandPlugin(management_config)
        management_plugin.add_bot_instance(self)
        management_command = plugins.commandplugin.bot_commands.management_cmds.ManagementCommands(management_config)
        management_plugin.register_command(management_command)
        self.compulsory_plugins = [("management", management_plugin)]

    def threadpool_exc_handler(self, etype, value, tb):
        traceback.print_exception(etype, value, tb)

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
            # TODO: Log this error
            traceback.print_exc()

    def register_plugin(self, plugin, name):
        ''' Registers plugin in our bot. If that plugin instance is already registered, do nothing.
        Warning! Order in which you register plugins matters. Plugin methods will be called directly in that
        order. So, the most important plugins e.g. logging should be registered first since other plugins
        may stop processing cycle by raising StanzaProcessed exception.
        If name is None, '''
        if name in self.plugins:
            return False
        if not plugin.add_bot_instance(self):
            return False
        self.plugins[name] = plugin
        return True

    def unregister_plugin(self, name):
        ''' Unregisters plugin from our bot. Raises ValueError if plugin was not registered previously '''
        plugin = self.plugins[name]
        plugin.remove_bot_instance(self)
        self.plugins.pop(name)

    def reload_config(self):
        self.config.reload()

    def reload_and_apply_config(self):
        self.config.reload()
        self.apply_config()

    def reload_plugin(self, name):
        old_plugin = self.plugins[name]
        plugin_config = self.config['plugins'][name]
        plugin = self.load_plugin(plugin_config, reload_module=True)
        self.plugins[name] = plugin
        old_plugin.shutdown()

    def load_plugin(self, plugin_config, reload_module=False):
        module_name = plugin_config['module']
        module = importlib.import_module(module_name)
        if reload_module:
            reload(module)
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
                self.register_plugin(plugin, plugin_name)

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

