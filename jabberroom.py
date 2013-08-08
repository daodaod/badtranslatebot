#!/usr/bin/env python
# -*- coding: utf-8 -*-

class JabberRoomUser(object):
    __slots__ = "nick", "jid", "affiliation", "role", "show", "status"

    def __init__(self, **kwargs):
        for item in self.__slots__:
            setattr(self, item, kwargs.get(item, None))

class JabberRoom(object):
    ''' Represents jabber room as seen by bot. 
    real_nickname is one that is assigned by jabber server.
    When one wants to change bot's nick, he should assign it to requested_nickname.   
    '''

    def __init__(self, room_jid):
        self.room_jid = room_jid
        self._real_nickname = None
        self._password = None
        self.requested_nickname = None
        self.temporary_nick_part = None
        self.temporary_nick_counter = 0
        self.users = {}
        self.last_checked = 0
        self.last_activity = 0

    def _set_password(self, password):
        self._password = password

    def _get_password(self):
        return self._password

    password = property(_get_password, _set_password)

    def _get_real_nickname(self):
        return self._real_nickname or ''

    def _set_real_nickname(self, new_nickname):
        self._real_nickname = new_nickname
        self.reset_temporary_nickname()

    real_nickname = property(_get_real_nickname, _set_real_nickname)

    def reset_temporary_nickname(self):
        ''' Reverts temporary_nickname to requested_nickname '''
        self.temporary_nick_part = None
        self.temporary_nick_counter = 0

    @property
    def temporary_nickname(self):
        return self.requested_nickname + (self.temporary_nick_part or '')

    def change_temporary_nick(self):
        ''' This function is called when bot is trying to find free nickname
        to enter the room'''
        self.temporary_nick_counter += 1
        self.temporary_nick_part = '_%d' % self.temporary_nick_counter

    def add_user(self, nick, user):
        self.users[nick] = user
        user.nick = nick

    def del_user(self, nick):
        self.users.pop(nick, None)

    def change_user_nick(self, user, nick, new_nick):
        old_user = self.users.pop(nick, user)
        self.users[new_nick] = old_user
        user.nick = new_nick

    def __str__(self):
        return "<Jabber conference %s/%s %r" % (self.room_jid, self.real_nickname, self.users)

    __repr__ = __str__


if __name__ == '__main__':
    room = JabberRoom('conf@example.org')
    nickname = 'bob'
    room.requested_nickname = 'bob'
    assert room.temporary_nickname == 'bob'
    room.change_temporary_nick()
    assert room.temporary_nickname == 'bob_1'
    room.real_nickname = 'Bob'
    assert room.temporary_nickname == 'bob'
    assert room.real_nickname == 'Bob'

