#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
import bot_commands
import re
import threadpool

class CommandPlugin(plugins.ThreadedPlugin):
    command_prefix = plugins.make_config_property('command_prefix')
    def __init__(self, config_section):
        super(CommandPlugin, self).__init__(config_section)
        self.command_bindings = {}
        self.commands_list = []
        self.command_re = re.compile(r'(%s\w+)' % re.escape(self.command_prefix), flags=re.UNICODE)


    def register_command(self, command):
        ''' Register command in a CommandPlugin. Won't do anything if there are conflicts '''

        added_commands = []
        has_failed = False
        try:
            for command_name, method in command.get_registered_commands().iteritems():
                bot_commands._add_command_handler(command_name, method, self.command_bindings)
                added_commands.append(command_name)
        except:
            has_failed = True
            raise
        finally:
            if has_failed:
                for command_name in added_commands:
                    self.command_bindings.pop(command_name, None)
        if not has_failed:
            self.commands_list.append(command)

    def unregister_command(self, command):
        ''' Unregisters a command. Raises ValueError if this command was not previously registered '''

        self.commands_list.remove(command)
        for command_name, method in command.get_registered_commands().iteritems():
            self.command_bindings.pop(command_name)

    @plugins.register_plugin_method
    def process_text_message(self, message, bot_instance, has_subject, is_from_me, **kwargs):
        if is_from_me or has_subject: return
        from_ = message.getFrom()
        text = message.getBody()
        split_text = self.command_re.split(text, maxsplit=1)
        if len(split_text) == 1:  # there is even no command prefix
            return
        command = split_text[1][len(self.command_prefix):].lower()
        method = self.command_bindings.get(command, None)
        if method is None:
            return
        left_side = split_text[0].strip().lower()
        if left_side:
            my_nickname = bot_instance.get_my_room_nickname(from_.getStripped())
            if my_nickname.lower() not in re.split(r'(\w+)', left_side, flags=re.UNICODE):
                return
        args = ''.join(split_text[2:]).strip()
        result = method(command, args, message=message, plugin=self, bot_instance=bot_instance)
        if isinstance(result, basestring):
            if result.strip():
                bot_instance.send_simple_reply(message, result)
        elif isinstance(result, threadpool.Task):
            self.add_task(result, bot_instance)
        raise plugins.StanzaProcessed

if __name__ == '__main__':
    class ExampleCommand(bot_commands.Command):
        @bot_commands.command_names('hello', 'hi', 'hithere')
        def boo(self, plugin, bot_instance):
            pass

        @bot_commands.command_names('nie')
        def foo(self, plugin, bot_instance):
            pass

    class ExampleCommand2(bot_commands.Command):
        @bot_commands.command_names('bye', 'bb', 'goodbye')
        def boo(self, plugin, bot_instance):
            pass

        @bot_commands.command_names('nie')
        def foo(self, plugin, bot_instance):
            pass
    e = ExampleCommand()
    e2 = ExampleCommand2()
    p = CommandPlugin(5)
    p.register_command(e)
    try:
        p.register_command(e2)
    except:
        pass
    p.unregister_command(e)
    print p.command_bindings
