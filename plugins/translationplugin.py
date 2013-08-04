#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
import gtranslate
import xmpp
import re
import random

class BadTranslatePlugin(plugins.ThreadedPlugin):
    def __init__(self, max_tasks, translations):
        self.translations = translations
        super(BadTranslatePlugin, self).__init__(max_tasks=max_tasks)

    def should_reply(self, text, my_nickname):
        ''' This routine checks, if bot's nickname is in the text, and if it is, replaces
        it with space.'''
        text_parts = re.split(r'(\w+)', text, flags=re.UNICODE)
        my_nickname_lower = my_nickname.lower()
        nick_present = False
        for i, part in enumerate(text_parts):
            if part.lower() == my_nickname_lower:
                nick_present = True
                text_parts[i - 1] = text_parts[i + 1] = u''
                text_parts[i] = u' '
        if not nick_present:
            if random.randrange(0, 300) < 10:
                return text
            return None
        return u''.join(text_parts)

    def preprocess_text(self, text):
        return text.strip().replace('?', '.')

    @plugins.register_plugin_method
    def process_text_message(self, message, bot_instance):
        assert isinstance(message, xmpp.Message)
        if message.getType() != 'groupchat':
            return
        if message.getSubject() is not None:
            return
        from_ = message.getFrom()
        if bot_instance.is_my_jid(from_):
            return
        text = message.getBody()
        my_nickname = bot_instance.get_my_room_nickname(from_.getStripped())
        text = self.preprocess_text(text)
        text = (self.should_reply(text, my_nickname) or '').strip()
        if not text:
            return
        task = plugins.ThreadedPluginTask(self, bot_instance, message, self.translate_text)
        task.set_args_kwargs(text)
        self.add_task(task, bot_instance)

    def translate_text(self, text):
        return gtranslate.bad_translate(text, iterations=self.translations)

    def on_task_result(self, task, translation):
        task.bot_instance.send_simple_reply(task.message, translation)
