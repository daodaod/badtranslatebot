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
        translation = self.text #gtranslate.bad_translate(self.text, iterations=20)
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
        text_parts = re.split(r'(\w+)', text, flags=re.UNICODE)
        my_nickname_lower = my_nickname.lower()
        nick_present = False
        for i, part in enumerate(text_parts):
            if part.lower() == my_nickname_lower:
                nick_present = True
                text_parts[i-1] = text_parts[i+1] = u''
                text_parts[i] = u' '
        if not nick_present:
            if random.randrange(0,300)<10:
                return text
            return None
        return u''.join(text_parts)

    def preprocess_text(self, text):
        return text.strip().replace('?', '.')
        
    def callback_message(self, conn, message):
        assert isinstance(message, xmpp.Message)
        # TODO: Add history logging
        if xmpp.NS_DELAY in message.getProperties():
            return
        if message.getSubject() is not None:
            return
        text = message.getBody()
        if text is None or not text.strip():
            return
        jid = message.getFrom()
        sender_nickname = jid.getResource()
        type_ = message.getType()
        if self.jid.bareMatch(jid):
            return
        print "Got message"
        print message.__str__(True)
        text = self.preprocess_text(text)
        if type_ == 'groupchat':
            conf = self.rooms.get(jid.getStripped())
            if conf is not None:
                my_nickname = conf.real_nickname
                if my_nickname == sender_nickname:
                    return
                text = self.should_reply(text, my_nickname)
                if not text:
                    return
        elif type_ =='chat':
            # Temp. workaround
            message.setType('groupchat')
            jid.setResource(None)
            message.setFrom(jid)
            self.send_simple_reply(message, text, private=False)
            return
        task = TranslationTask(text, (lambda result, m=message, private=(message.getType()=='chat'):
                                    self.locked_send_simple_reply(m, result, private)))
        try:
            self.thread_pool.add_task(task)
        except Queue.Full:
            # Maybe send an excuse?
            pass
        
     
        
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
    pool = threadpool.TaskPool(workers_num=int(config['badtranslate']['translation_threads']),
                               max_task_num=int(config['badtranslate']['translation_queue_limit']),
                               exception_handler=traceback.print_exception)
    bot = TranslatorBot(login, password, pool, res=resource)
    for name, conf in config['rooms'].iteritems():
        bot.add_room(conf['jid'], conf['nickname'], conf.get('password'))    
    try:
        while True:
            try:
                bot.serve_forever()
            except Exception, ex:
                print "Exception happened within serve_forever!"
                traceback.print_exc()
    finally:
        print "Shutting down. Good bye."
        if bot.connected:
            bot.disconnect()
        pool.stop()
        pool.join()
        
        
        
        
        
        
