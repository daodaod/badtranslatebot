#!/usr/bin/env python
# -*- coding: utf-8 -*-

KLASS = 'ChatvdvoemPlugin'

import xmpp
import plugins.utils
import sys
import threading
sys.path.append('../chatvdvoem-client')
import chatvdvoem
import chatkey

class PluggedChatter(chatvdvoem.Chatter):
    def __init__(self, chat_key_extractor, room_jid, plugin, logger=None):
        super(PluggedChatter, self).__init__(chat_key_extractor, logger=logger)
        self.room_jid = room_jid
        self.plugin = plugin

    def on_message(self, message):
        self.plugin.send(self.room_jid, message, event='message')

    def on_start_chat(self):
        self.plugin.send(self.room_jid, u"/me Воплотился", event='start_chat')

    def on_shutdown(self):
        self.plugin.send_message(self.room_jid, "/me Выветрился", event='stop_chat')


class ChatvdvoemPlugin(plugins.ThreadedPlugin):
    def __init__(self, config_section):
        super(ChatvdvoemPlugin, self).__init__(config_section)
        self.chatvdvoem_instance = None
        self.commutated = set([u'ЛисаАлиса', u'Боб'])

    def chatvdvoem_runner(self):
        self.chatvdvoem_instance = chatvdvoem.Chatter(chatkey.get_chat_key)

    def add_pending_message(self, text, room_jid):
        chatvdvoem_instance = self.chatvdvoem_instance
        if chatvdvoem_instance is None:
            self.chatvdvoem_instance = chatvdvoem_instance = PluggedChatter(chatkey.get_chat_key, room_jid=room_jid, plugin=self)
            self.chatvdvoem_thread = threading.Thread(target=self.serve_chatvdvoem_conversation, args=(chatvdvoem_instance,))
            self.chatvdvoem_thread.setDaemon(True)
            self.chatvdvoem_thread.start()
        chatvdvoem_instance.send_message(text)

    def serve_chatvdvoem_conversation(self, instance):
        try:
            instance.serve_conversation()
        except Exception, ex:
            self.logger.error("Exception happened while serving chatvdvoem conversation", exc_info=1)
        self.chatvdvoem_instance = None

    def shutdown(self):
        self.kill_chatvdvoem()

    def send(self, room_jid, text, event):
        message = self.bot_instance.build_message(text)
        message.setTo(room_jid)
        message.setType('groupchat')
        commutated_tag = message.addChild('chatvdvoem')
        commutated_tag.setAttr('event', event)
        if event == 'message':
            for nick in self.commutated:
                child = commutated_tag.addChild('nickname')
                child.setData(nick)
        self.bot_instance.send_message(message)

    def kill_chatvdvoem(self):
        chatvdvoem_instance = self.chatvdvoem_instance
        if chatvdvoem_instance is None:
            return
        chatvdvoem_instance.send_stop_chat()
        chatvdvoem_instance.quit()

    def is_commutated_to_me(self, message, my_nickname):
        commutated_tag = message.getTag('chatvdvoem')
        if not commutated_tag: return False
        for tag in commutated_tag.getTags('nickname'):
            if tag.getData() == my_nickname:
                return True
        return False

    @plugins.register_plugin_method
    def process_text_message(self, message, has_subject, is_from_me, is_groupchat):
        if has_subject or is_from_me or (not is_groupchat):
            return
        assert isinstance(message, xmpp.Message)
        from_ = message.getFrom()
        text = message.getBody()
        my_nickname = self.bot_instance.get_my_room_nickname(from_.getStripped())
        if not self.is_commutated_to_me(message, my_nickname):
            text_parts = plugins.utils.split_by_nickname(text, my_nickname)
            if len(text_parts) <= 3 or text_parts[1].lower() != my_nickname.lower():
                return
            text = ''.join(text_parts[3:])
        self.add_pending_message(text, from_.getStripped())
