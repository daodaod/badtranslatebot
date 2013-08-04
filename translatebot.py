#!/usr/bin/env python
# -*- coding: utf-8 -*-

import Queue
import random
import threadpool
import gtranslate
import re
import persistentbot
import threading
import xmpp

class TranslationTask(threadpool.Task):
    def __init__(self, text, result_callback):
        self.text = text
        self.result_callback = result_callback
        super(TranslationTask, self).__init__()

    def execute(self):
        translation = gtranslate.bad_translate(self.text, iterations=20)
        self.result_callback(translation)

class TranslatorBot(persistentbot.PersistentJabberBot):
    def __init__(self, username, password, thread_pool, res=None, debug=False,
        privatedomain=False, acceptownmsgs=False, command_prefix=''):
        self.thread_pool = thread_pool
        self.send_lock = threading.Lock()
        super(TranslatorBot, self).__init__(
                username, password, res=res, debug=debug,
                privatedomain=privatedomain, acceptownmsgs=acceptownmsgs,
                command_prefix=command_prefix)

    def locked_send_simple_reply(self, *args, **kwargs):
        with self.send_lock:
            self.send_simple_reply(*args, **kwargs)

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

    def process_text_message(self, mess):
        super(TranslatorBot, self).process_text_message(mess)
        assert isinstance(mess, xmpp.Message)
        from_ = mess.getFrom()
        text = mess.getBody()
        if mess.getSubject() is not None:
            return
        if self.is_my_jid(from_):
            return
        if mess.getType() == 'groupchat':
            my_nickname = self.get_my_room_nickname(from_.getStripped())
            text = self.preprocess_text(text)
            text = self.should_reply(text, my_nickname)
            if not text:
                return
            task = TranslationTask(text, (lambda result, m=mess:self.locked_send_simple_reply(m, result)))
            try:
                self.thread_pool.add_task(task)
            except Queue.Full:
                # TODO: Maybe send an excuse?
                pass
        elif mess.getType() == 'chat':
            reply_mess = mess.buildReply(text)
            reply_mess.setType('groupchat')
            to_jid = reply_mess.getTo()
            to_jid.setResource(None)
            self.send_message(reply_mess)


if __name__ == '__main__':
    import logging
    logger = logging.getLogger('jabberbot')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    logger.addHandler(ch)


    import configobj
    config = configobj.ConfigObj('bot.config')
    login = config['jabber_account']['jid']
    password = config['jabber_account']['password']
    resource = config['jabber_account']['resource']

    # TODO: Fix this mess
    import traceback
    import time
    import plugins.chatlogplugin
    pool = threadpool.TaskPool(workers_num=int(config['badtranslate']['translation_threads']),
                               max_task_num=int(config['badtranslate']['translation_queue_limit']),
                               exception_handler=traceback.print_exception)
    bot = TranslatorBot(login, password, pool, res=resource)

    log_path = config['chatlog']['log_path']
    chatlog_plugin = plugins.chatlogplugin.ChatlogPlugin(log_path)
    bot.register_plugin(chatlog_plugin)
    for name, conf in config['rooms'].iteritems():
        bot.add_room(conf['jid'], conf['nickname'], conf.get('password'))
    try:
        while True:
            try:
                bot.serve_forever()
            except Exception, ex:
                print "Exception happened within serve_forever!"
                traceback.print_exc()
        time.sleep(1)  # Let us not rape the server
    finally:
        print "Shutting down. Good bye."
        if bot.connected:
            bot.disconnect()
        pool.stop()
        pool.join()






