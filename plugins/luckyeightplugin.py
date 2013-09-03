# -*- coding: utf-8 -*-

KLASS = 'LuckyEightPlugin'

import plugins
import random
import xmpp
import plugins.utils
import re

class LuckyEightPlugin(plugins.ThreadedPlugin):
    def preprocess_text(self, text):
        return text.rstrip('?')

    @plugins.register_plugin_method
    def process_text_message(self, message, has_subject, is_from_me, is_groupchat):
        if has_subject or is_from_me or (not is_groupchat):
            return
        assert isinstance(message, xmpp.Message)
        from_ = message.getFrom()
        text = message.getBody()
        my_nickname = self.bot_instance.get_my_room_nickname(from_.getStripped())
        if not text.rstrip().endswith('??'):
            return
        text = self.preprocess_text(text)
        new_text = plugins.utils.is_message_for_me(text, my_nickname, startswith_nick=True)
        if not new_text:
            return
        separators = [u' или ']
        for separator in separators:
            choices = [s.strip() for s in re.split(re.escape(separator), new_text, flags=re.I | re.U) if s.strip()]
            if len(choices) != 1:
                break
        else:
            return
        self.send_simple_reply(message, random.choice(choices), include_nick=True)
        raise plugins.StanzaProcessed
