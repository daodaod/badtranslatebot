#!/usr/bin/env python
# -*- coding: utf-8 -*-


import jabberbot
import time
import xmpp
import jabberroom
import threading
import threadpool
import traceback
import sys

class PersistentJabberBot(jabberbot.JabberBot):
    # TODO: Get rid of jabberbot.JabberBot, we will have our own base soon
    # If nothing was heard from the room for ROOM_CHECK_PERIOD seconds, check, if we are still there.
    ROOM_CHECK_PERIOD = 3600 * 24
    # Do not re-join room more often than once per this seconds.
    ROOM_CHECK_FREQUENCY = 10
    PING_FREQUENCY = 30
    PING_TIMEOUT = 10

    def __init__(self, username, password, res=None, debug=False, privatedomain=False, acceptownmsgs=False):
        self.stopped = False
        self.rooms = {}
        handlers = [('message', self.callback_message),
                    ('presence', self.callback_presence),
                ]
        # Since xmpppy dispatcher.send is not thread safe
        # we will lock send_stanza method to linearize all conn.send methods
        self.send_lock = threading.Lock()
        next_constructor = super(PersistentJabberBot, self).__init__
        next_constructor(username, password, res=res, debug=debug,
                         privatedomain=privatedomain, acceptownmsgs=acceptownmsgs,
                         handlers=handlers)

    def callback_presence(self, conn, presence):
        """
        Presence handler.

        :param conn: Connection dispatcher
        :type conn: xmpp.dispatcher.Dispatcher
        :param presence: XMPP presence
        :type presence: xmpp.Presence
        """
        self.process_presence(presence)
        if presence.getType() == 'error':
            self.process_presence_error(presence)
        else:
            if xmpp.NS_MUC_USER in presence.getProperties():
                self.process_room_presence(presence)
        # TODO: Get rid of this super call
        super(PersistentJabberBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, message):
        """
        Message handler.

        :param conn: Connection dispatcher
        :type conn: xmpp.dispatcher.Dispatcher
        :param message: XMPP message
        :type message: xmpp.Message
        """
        self.process_message(message)
        if message.getError() is not None:
            self.process_message_error(message)
        elif xmpp.NS_DELAY in message.getProperties():
            self.process_delayed_message(message)
        elif message.getBody():
            has_subject = message.getSubject() is not None
            is_from_me = self.is_my_jid(message.getFrom())
            is_groupchat = message.getType() == 'groupchat'
            self.process_text_message(message, has_subject=has_subject, is_from_me=is_from_me, is_groupchat=is_groupchat)

    def process_message(self, message):
        """
        This routine handles all xmpp.Message stanzas received by client.

        :param message: xmpp message stanza
        :type message: xmpp.Message
        """
        pass

    def process_text_message(self, message, has_subject, is_from_me, is_groupchat) :
        """
        This routine handles all messages with body tag.

        :param message: xmpp message stanza.
        :type message: xmpp.Message

        :param has_subject: True if there is a subject tag in the message, such message may be received when someone sets the topic in MUC chat.
        :type has_subject: bool

        :param is_from_me: True if this message was sent by the client. It's just the result of `is_my_jid(message.getFrom())` call.
        :type is_from_me: bool

        :param is_groupchat: True if message type is `groupchat`
        :type is_groupchat: bool
        """
        pass

    def process_presence(self, presence):
        ''' This routine handles all presence stanzas'''
        pass

    def process_room_presence(self, presence):
        assert isinstance(presence, xmpp.Presence)
        jid = presence.getFrom()
        assert isinstance(jid, xmpp.JID)
        pres_jid = presence.getJid()
        pres_affiliation = presence.getAffiliation()
        pres_role = presence.getRole()
        pres_show = presence.getShow()
        pres_status = presence.getStatus()
        user_info = jabberroom.JabberRoomUser(jid=pres_jid, affiliation=pres_affiliation,
                                              role=pres_role, show=pres_show, status=pres_status)
        current_time = time.time()
        room_jid = jid.getStripped()
        room_nick = jid.getResource()
        room = self.get_room(room_jid)
        # Manage participants list
        if presence.getNick() is not None and presence.getStatusCode() == '303':
            room.change_user_nick(user_info, room_nick, presence.getNick())
        elif presence.getType() == 'unavailable':
            room.del_user(room_nick)
        else:
            room.add_user(room_nick, user_info)
        # Manage bot enter/left events
        is_self_presence = (presence.getStatusCode() == '110')
        if room.real_nickname and room.real_nickname == room_nick:
            is_self_presence = True
        if not is_self_presence:
            return
        room.real_nickname = room_nick
        if presence.getType() == 'unavailable':
            room.real_nickname = None
            room.last_activity = 0
        else:
            room.last_activity = current_time

    def process_presence_error(self, presence):
        jid = presence.getFrom()
        room_jid = jid.getStripped()
        if room_jid not in self.rooms:
            return
        room = self.get_room(room_jid)
        room.change_temporary_nick()
        room.last_activity = 0

    def is_my_jid(self, jid):
        ''' Determines, if that jid is our jid. It could be just our jabber login,
        or our jid in some conference.'''
        if self.jid.bareMatch(jid):
            return True
        elif jid.getResource() == self.get_my_room_nickname(jid.getStripped()):
            if jid.getResource():
                return True
        return False

    def get_my_room_nickname(self, room_jid):
        ''' Returns our nickname in that room, or None, if there isn't such.'''
        room = self.rooms[room_jid]
        if room is not None:
            return room.real_nickname

    def get_room_user(self, room_jid, nickname):
        room = self.rooms.get(room_jid)
        if room is None:
            return None
        return room.users.get(nickname)

    def get_room_user_by_jid(self, jid):
        """

        :type jid xmpp.JID
        :param jid:
        :return:
        """
        return self.get_room_user(jid.getStripped(), jid.getResource())

    def build_room_presence(self, room, username, password=None, type_=None):
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
        ''' Send join presence. This function doesn't touch self.rooms variable at all.
        Instead, when server responses with "ok" presence, we add that room to self.rooms'''
        join_pres = self.build_room_presence(room, username, password)
        return self.send_stanza(join_pres)

    def leave_room(self, room, username=None):
        ''' The same as join, but send "unavailable" presence '''
        leave_pres = self.build_room_presence(room, username, type_='unavailable')
        return self.send_stanza(leave_pres)

    def kick(self, room, nick, reason=None):
        raise NotImplementedError

    def send_tune(self, song, debug=False):
        raise NotImplementedError

    def invite(self, room, jid, reason=None):
        raise NotImplementedError

    def add_task(self, task):
        ''' Add task to threadpool. If wait queue is full, return False, otherwise return True '''
        return self.threadpool.add_task(task)

    def get_room(self, room_jid):
        room = self.rooms.get(room_jid, None)
        if room is None:
            room = jabberroom.JabberRoom(room_jid)
            self.rooms[room_jid] = room
        return room

    def add_room(self, room_jid, nickname, password):
        room = self.get_room(room_jid)
        room.requested_nickname = nickname
        room.password = password

    def check_rooms(self):
        current_time = time.time()
        for room_jid, room in self.rooms.iteritems():
            if current_time - room.last_activity < self.ROOM_CHECK_PERIOD:
                continue
            if current_time - room.last_checked < self.ROOM_CHECK_FREQUENCY:
                continue
            room.last_checked = current_time
            self.join_room(room_jid, room.temporary_nickname, room.password)

    def send_message(self, message):
        return self.send_stanza(message)

    def send_stanza(self, stanza):
        conn = self.conn
        if conn is not None:
            with self.send_lock:
                return conn.send(stanza)

    def send_simple_reply(self, mess, text, private=False, include_nick=False):
        if include_nick and mess.getType() == 'groupchat':
            text = '%s: %s' % (mess.getFrom().getResource(), text)
        if mess.getType() == 'chat':
            private = True
        super(PersistentJabberBot, self).send_simple_reply(mess, text, private=private)

    def idle_proc(self):
        super(PersistentJabberBot, self).idle_proc()
        self.check_rooms()

    def process(self, timeout):
        return self.conn.Process(timeout)

    def on_ping_timeout(self):
        self.conn.disconnect()

    @property
    def connected(self):
        return self.conn is not None and self.conn.connected

    def connect(self):
        conn = super(PersistentJabberBot, self).connect()
        if conn is not None:
            conn.UnregisterDisconnectHandler(self.conn.DisconnectHandler)
        return conn

    def disconnect(self):
        conn = self.conn
        if conn is not None:
            conn.disconnect()

    def on_disconnect(self):
        for room in self.rooms.itervalues():
            room.last_activity = 0

    def quit(self):
        ''' Stops the bot from serving'''
        self.stopped = True
        self.shutdown()

    def shutdown(self):
        if self.connected:
            self.disconnect()

    def serve_forever(self):
        ''' Server until quit() is called or exception inside is raised.
        So, if you want bot to be really persistent, you should put serve_forever 
        within try-except in a loop and handle exceptions inside.'''
        while not self.stopped:
            result = None
            if self.connected:
                result = self.process(1)
            if result is None:
                if self.connected:
                    self.disconnect()
                self.on_disconnect()
                self.conn = None
                conn = self.connect()
                if conn is not None:
                    conn.sendInitPresence()
                if not self.connected:
                    continue
            self.idle_proc()

    def serve_really_forever(self, exception_handler=None):
        try:
            while not self.stopped:
                try:
                    self.serve_forever()
                except Exception:
                    if exception_handler is not None:
                        exception_handler(*sys.exc_info())
            time.sleep(1)  # Let us not rape the server
        finally:
            if self.connected:
                self.disconnect()
            self.on_exit()

    def on_exit(self):
        pass

if __name__ == '__main__':
    import configobj

    config = configobj.ConfigObj('config/alice.config')
    acc_info = config['jabber_account']
    login = acc_info['jid']
    password = acc_info['password']
    resource = acc_info.get('resource', None)

    bot = PersistentJabberBot(login, password, res=resource)

    for name, room in config['rooms'].iteritems():
        bot.add_room(room['jid'], room['nickname'], room.get('password'))

    bot.serve_really_forever(traceback.print_exception)


