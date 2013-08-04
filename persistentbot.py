#!/usr/bin/env python
# -*- coding: utf-8 -*-

import jabberbot
import time
import xmpp
import jabberroom
import threading
import threadpool
import traceback

class PersistentJabberBot(jabberbot.JabberBot):
    # TODO: Get rid of jabberbot.JabberBot, we will have our own base soon
    # If nothing was heard from the room for ROOM_CHECK_PERIOD seconds, check, if we are still there.
    ROOM_CHECK_PERIOD = 3600 * 24
    # Do not re-join room more often than once per this seconds.
    ROOM_CHECK_FREQUENCY = 10
    PING_FREQUENCY = 30
    PING_TIMEOUT = 10

    def __init__(self, username, password, res=None, debug=False,
                 pool_workers=1, privatedomain=False, acceptownmsgs=False):
        self.stopped = False
        self.rooms = {}
        self.method_plugins = {}  # method name -> [list of plugins]
        handlers = [('message', self.callback_message),
                    ('presence', self.callback_presence),
                    ('iq', self.callback_iq)]
        # Since xmpppy dispatcher.send is not thread safe
        # we will lock send_stanza method to linearize all conn.send methods
        self.send_lock = threading.Lock()
        self.threadpool = threadpool.TaskPool(workers_num=pool_workers,
                                              max_task_num=pool_workers,
                                              exception_handler=self.threadpool_exc_handler)
        next_constructor = super(PersistentJabberBot, self).__init__
        next_constructor(username, password, res=res, debug=debug,
                         privatedomain=privatedomain, acceptownmsgs=acceptownmsgs,
                         handlers=handlers)

    def threadpool_exc_handler(self, etype, value, tb):
        traceback.print_exception(etype, value, tb)

    def callback_presence(self, conn, presence):
        assert isinstance(presence, xmpp.Presence)
        self.process_presence(presence)
        if presence.getType() == 'error':
            self.process_error_presence(presence)
        else:
            if xmpp.NS_MUC_USER in presence.getProperties():
                self.process_room_presence(presence)
        # TODO: Get rid of this super call
        super(PersistentJabberBot, self).callback_presence(conn, presence)

    def callback_message(self, conn, message):
        assert isinstance(message, xmpp.Message)
        self.process_message(message)
        if message.getError() is not None:
            self.process_message_error(message)
        elif xmpp.NS_DELAY in message.getProperties():
            self.process_delayed_message(message)
        elif message.getBody():
            self.process_text_message(message)

    def callback_iq(self, conn, iq):
        # TODO: Add some pretty iq response
        pass

    def process_message(self, message):
        ''' This routine handles all messages, received by bot.'''
        self.handle_plugins(self.process_message.__name__, message)

    def process_message_error(self, message):
        ''' This routine handles all message stanzas with error tag set.'''
        pass

    def process_delayed_message(self, message):
        ''' This routine handles delayed messages. Those are usually sent as history,
        when bot enters the room.'''
        pass

    def process_text_message(self, message):
        ''' This routine handles all messages with body tag.'''
        self.handle_plugins(self.process_text_message.__name__, message)

    def process_presence(self, presence):
        ''' This routine handles all presence stanzas'''
        self.handle_plugins(self.process_presence.__name__, presence)

    def process_room_presence(self, presence):
        assert isinstance(presence, xmpp.Presence)
        jid = presence.getFrom()
        assert isinstance(jid, xmpp.JID)
        pres_jid = presence.getJid()
        pres_affiliation = presence.getAffiliation()
        pres_role = presence.getRole()
        pres_show = presence.getShow()
        pres_status = presence.getStatus()
        user_info = [pres_jid, pres_affiliation, pres_role, pres_show, pres_status]
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

    def handle_plugins(self, methodname, *args, **kwargs):
        for plugin in self.method_plugins.get(methodname, []):
            func = getattr(plugin, methodname)
            kwargs['bot_instance'] = self
            try:
                func(*args, **kwargs)
            except plugins.StanzaProcessed:
                break  # TODO: Maybe add logging.log here?

    def register_plugin(self, plugin):
        ''' Registers plugin in our bot. If that plugin instance is already registered, do nothing.
        Warning! Order in which you register plugins matters. Plugin methods will be called directly in that
        order. So, the most important plugins e.g. logging should be registered first since other plugins
        may stop processing cycle by raising StanzaProcessed exception.'''
        if not plugin.add_bot_instance(self):
            return
        for methodname in plugin.get_registered_methods_names():
            plugins_list = self.method_plugins.setdefault(methodname, [])
            plugins_list.append(plugin)

    def unregister_plugin(self, plugin):
        ''' Unregisters plugin from our bot. Raises ValueError if plugin was not registered previously '''
        plugin.remove_bot_instance(self)
        for methodname in plugin.get_registered_methods_names():
            plugins_list = self.method_plugins[methodname]
            plugins_list.remove(plugin)
            if not plugins_list:
                self.method_plugins.pop(methodname)

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
        room = self.rooms.get(room_jid)
        if room is not None:
            return room.real_nickname

    def get_room_user(self, room_jid, nickname):
        room = self.rooms.get(room_jid)
        if room is None:
            return None
        return room.users.get(nickname)

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

    def on_exit(self, wait_for_threadpool=False):
        self.threadpool.stop()
        if wait_for_threadpool:
            self.threadpool.join()


if __name__ == '__main__':
    import configobj
    import plugins.chatlogplugin
    import plugins.translationplugin
    import plugins.commandplugin
    import plugins.commandplugin.bot_commands
    import plugins.commandplugin.bot_commands.testcommand
    config = configobj.ConfigObj('bot.config')
    login = config['jabber_account']['jid']
    password = config['jabber_account']['password']
    resource = config['jabber_account']['resource']

    bot = PersistentJabberBot(login, password, res=resource, pool_workers=10)

    log_path = config['plugins']['chatlog']['log_path']

    chatlog_plugin = plugins.chatlogplugin.ChatlogPlugin(log_path)
    bot.register_plugin(chatlog_plugin)

    command_plugin = plugins.commandplugin.CommandPlugin(5)
    bot.register_plugin(command_plugin)

    hello_command = plugins.commandplugin.bot_commands.testcommand.TestCommand()
    command_plugin.register_command(hello_command)

    translation_config = config['plugins']['translation']
    max_concurrent_translations = int(translation_config['max_concurrent_translations'])
    translation_iterations = int(translation_config['translation_iterations'])
    badtranslate_plugin = plugins.translationplugin.BadTranslatePlugin(max_tasks=max_concurrent_translations,
                                                                       translations=translation_iterations)
    bot.register_plugin(badtranslate_plugin)
    for name, room in config['rooms'].iteritems():
        bot.add_room(room['jid'], room['nickname'], room.get('password'))

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
        bot.on_exit()



