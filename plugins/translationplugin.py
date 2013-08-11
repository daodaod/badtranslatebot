#!/usr/bin/env python
# -*- coding: utf-8 -*-

PLUGIN_CLASS = 'BadTranslatePlugin'

import gtranslate
import xmpp
import random
import plugins.utils

class BadTranslatePlugin(plugins.ThreadedPlugin):
    translations = plugins.make_config_property('translations', int, default=1)
    reply_probability = plugins.make_config_property('reply_probability', float, default=0)
    def should_reply(self, text, my_nickname):
        ''' This routine checks, if bot's nickname is in the text, and if it is, replaces
        it with space.'''
        new_text = plugins.utils.remove_nickname(text, my_nickname)
        if new_text != text or random.random() < self.reply_probability:
            return new_text
        return None

    def preprocess_text(self, text):
        return text.strip().replace('?', '.')

    @plugins.register_plugin_method
    def process_text_message(self, message, has_subject, is_from_me, is_groupchat):
        if has_subject or is_from_me or (not is_groupchat):
            return
        assert isinstance(message, xmpp.Message)
        from_ = message.getFrom()
        text = message.getBody()
        my_nickname = self.bot_instance.get_my_room_nickname(from_.getStripped())
        text = self.preprocess_text(text)
        text = (self.should_reply(text, my_nickname) or '').strip()
        if not text:
            return
        self.add_task(plugins.ThreadedPluginTask(self, self.translate_text, text, message))

    def translate_text(self, text, message):
        result = gtranslate.bad_translate(text, iterations=self.translations)
        self.send_simple_reply(message, result)

