#!/usr/bin/env python
# -*- coding: utf-8 -*-

PLUGIN_CLASS = 'BadTranslatePlugin'

import plugins
import gtranslate
import xmpp
import re
import random
import threadedplugin

class BadTranslatePlugin(plugins.ThreadedPlugin):
    translations = plugins.make_config_property('translations', int, default=1)
    reply_probability = plugins.make_config_property('reply_probability', float, default=0)
    def should_reply(self, text, my_nickname):
        ''' This routine checks, if bot's nickname is in the text, and if it is, replaces
        it with space.'''
        # The idea is to catch nickname with non-alphabetic character after it.
        text_parts = re.split(r'(%s(?:\W|$)|\w+)' % re.escape(my_nickname), text, flags=re.UNICODE | re.IGNORECASE)
        print '|'.join(text_parts)
        my_nickname_lower = my_nickname.lower()
        nick_present = False
        for i, part in enumerate(text_parts):
            part_lower = part.lower()
            # Maybe it's the case when we captured non-alphabetic character?
            if len(part_lower) == len(my_nickname_lower) + 1:
                if part_lower and not part_lower[-1].isalpha():
                    # Cool, cut it away!
                    part_lower = part_lower[:-1]
            if part_lower == my_nickname_lower:
                nick_present = True
                text_parts[i - 1] = text_parts[i + 1] = u''
                text_parts[i] = u' '
        if not nick_present:
            if random.random() < self.reply_probability:
                return text
            return None
        return u''.join(text_parts)

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
        self.bot_instance.send_simple_reply(message, result)

