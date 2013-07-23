#!/usr/bin/env python
# -*- coding: utf-8 -*-

import jabberbot
import xmpp
import logging
import time

# TODO: Do something with this
logger = logging.getLogger('jabberbot')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)


class JabberConference(object):
    def __init__(self, conf_jid):
        self.conf_jid = conf_jid
        self.nickname = None
        self._password = None
        self.temporary_nick_part = None
        self.temporary_nick_counter = 0
        self.users = {}
        self.last_checked = 0
        self.last_activity = 0
        
    def next_temporary_nick(self):
        self.temporary_nick_counter += 1
        self.temporary_nick_part = '_%d'%self.temporary_nick_counter
        
    def set_password(self, password):
        self._password = password
        
    def get_password(self):
        return self._password
    
    password = property(get_password, set_password)
        
    def get_nickname(self):
        return self.nickname or ''
    
    def get_temporary_nickname(self):
        return self.nickname + (self.temporary_nick_part or '')
    
    def update_nickname(self, new_nickname):
        self.nickname = new_nickname
        self.temporary_nick_part = None
        self.temporary_nick_counter = 0
        
    def add_user(self, nick, user):
        self.users[nick] = user
        
    def del_user(self, nick):
        self.users.pop(nick, None)
        
    def change_user_nick(self, user, nick, new_nick):
        old_user = self.users.pop(nick, user)
        # TODO: Change his nick in object
        self.users[new_nick] = old_user
        
    def __str__(self):
        return "<Jabber conference %s/%s %r"%(self.conf_jid, self.get_nickname(), self.users.keys())
    
    __repr__ = __str__
    
    
class PersistentJabberBot(jabberbot.JabberBot):
    # If nothing was heard from the conference for 24 hours, check, if we are still there.
    CONFERENCE_CHECK_PERIOD = 3600*24
    # Do not re-join conference more often than once per this seconds.
    CONFERENCE_CHECK_FREQUENCY = 10
    PING_FREQUENCY = 30
    PING_TIMEOUT = 10

    def __init__(self, username, password, res=None, debug=False, 
        privatedomain=False, acceptownmsgs=False, command_prefix=''):
        
        self.stopped = False
        self.conferences = {}
        self.conference_watchlist = {} # conference_jid -> [nickname, temporary_part, last_checked]
        
        handlers = [('message', self.callback_message),
                    ('presence', self.callback_presence),
                    ('iq', self.callback_iq)]
        next_constructor = super(PersistentJabberBot, self).__init__
        next_constructor(username, password, res=res, debug=debug,
                         privatedomain=privatedomain, acceptownmsgs=acceptownmsgs,
                         handlers=handlers, command_prefix=command_prefix)
                
    def callback_presence(self, conn, presence):
        if presence.getType() == 'error':
            self.on_error_presence(presence)
        else:
            if xmpp.NS_MUC_USER in presence.getProperties():
                self.on_conference_presence(presence)
        super(PersistentJabberBot, self).callback_presence(conn, presence)
        
    def on_error_presence(self, presence):
        jid = presence.getFrom()
        conf_jid = jid.getStripped()
        if conf_jid not in self.conferences:
            return
        conf = self.get_conference(conf_jid)
        conf.next_temporary_nick()
        conf.last_activity = 0
        
    def get_conference(self, conf_jid):
        conf = self.conferences.get(conf_jid, None)
        if conf is None:
            conf = JabberConference(conf_jid)
            self.conferences[conf_jid] = conf
        return conf
        
    def on_conference_presence(self, presence):
        assert isinstance(presence, xmpp.Presence)
        jid = presence.getFrom()
        assert isinstance(jid, xmpp.JID)
        current_time = time.time()
        conf_jid = jid.getStripped()
        conf_nick = jid.getResource()
        conf = self.get_conference(conf_jid)
        is_self_presence = (presence.getStatusCode() == '110')
        if conf.nickname and conf.nickname == conf_nick:
            is_self_presence = True
        if is_self_presence: 
            conf.update_nickname(conf_nick)
            if presence.getType() == 'unavailable':
                conf.last_activity = 0
            else:
                conf.last_activity = current_time
        else:
            conf.last_activity = current_time
            if presence.getNick() is not None and presence.getStatusCode()=='303':
                conf.change_user_nick(None, conf_nick, presence.getNick())
            elif presence.getType() == 'unavailable':
                conf.del_user(conf_nick)
            else:
                conf.add_user(conf_nick, None)
        
    def callback_iq(self, conn, iq):
        # TODO: Add some pretty iq response
        pass
        
    def process(self, timeout):
        return self.conn.Process(timeout)        
        
    def create_room_presence(self, room, username, password=None, type_=None):
        if username is None:
            username = self.jid.getNode()
        my_room_JID = '/'.join((room, username))
        pres = xmpp.Presence(to=my_room_JID)
        if password is not None:
            pres.setTag('x', namespace=xmpp.NS_MUC).setTagData('password', password)
        if type_ is not None:
            pres.setType(type_)
        return pres
        
    def join_room(self, room, username=None, password=None):
        join_pres = self.create_room_presence(room, username, password)
        return self.send_stanza(join_pres)
    
    def leave_room(self, room, username=None):
        leave_pres = self.create_room_presence(room, username, type_='unavailable')
        return self.send_stanza(leave_pres)
    
    def on_ping_timeout(self):
        self.conn.disconnect()
        
    @property
    def connected(self):
        return self.conn is not None and self.conn.connected
    
    def connect(self):
        conn = super(PersistentJabberBot, self).connect()
        if conn is not None:
            conn.UnregisterDisconnectHandler(bot.conn.DisconnectHandler)
        return conn
    
    def disconnect(self):
        conn = self.conn
        if conn is not None:
            conn.disconnect()
            
    def add_conference(self, conf_jid, nickname, password):
        conf = self.get_conference(conf_jid)
        conf.update_nickname(nickname)
        conf.set_password(password)
        
    def send_message(self, mess):
        return self.send_stanza(mess)
        
    def send_stanza(self, stanza):
        conn = self.conn
        if conn is not None:
            return conn.send(stanza)

    def idle_proc(self):
        super(PersistentJabberBot, self).idle_proc()
        self.check_conferences()
        
    def check_conferences(self):
        current_time = time.time()
        for conf_jid, conf in self.conferences.iteritems():
            if current_time - conf.last_activity < self.CONFERENCE_CHECK_PERIOD:
                continue
            if current_time - conf.last_checked < self.CONFERENCE_CHECK_FREQUENCY:
                continue
            conf.last_checked = current_time
            self.join_room(conf_jid, conf.get_temporary_nickname(), conf.password)
            
    def on_disconnect(self):
        for conf_jid, conf in self.conferences.iteritems():
            conf.last_activity = 0

    
class TranslatorBot(PersistentJabberBot):
    def __init__(self, username, password, res=None, debug=False, 
        privatedomain=False, acceptownmsgs=False, command_prefix=''):
        super(TranslatorBot, self).__init__(
                username, password, res=res, debug=debug, 
                privatedomain=privatedomain, acceptownmsgs=acceptownmsgs,
                command_prefix=command_prefix)
        
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
        print self.jid, jid
        if self.jid.bareMatch(jid):
            return
        if type_ == 'groupchat':
            conf = self.conferences.get(jid.getStripped())
            if conf is not None:
                if conf.get_nickname() == sender_nickname:
                    return
        import gtranslate
        text = gtranslate.bad_translate(text, iterations=20)
        self.send_simple_reply(message, text)
                
        
if __name__ == '__main__':
    import configobj
    config = configobj.ConfigObj('bot.config')
    login = config['jabber_account']['jid']
    password = config['jabber_account']['password']
    resource = config['jabber_account']['resource']
    bot = TranslatorBot(login, password, resource)
    for name, conf in config['conferences'].iteritems():
        bot.add_conference(conf['jid'], conf['nickname'], conf.get('password'))    
    
    while True:
        result = None
        if bot.connected:
            result = bot.process(1)
        if result is None:
            print "Result is None!"
            if bot.connected:
                bot.disconnect()
            bot.on_disconnect()
            bot.conn = None
            bot.connect()
            if not bot.connected:
                continue
        bot.idle_proc()
        
        
        
        
        
