#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
import os
import time
import hashlib
import cgi
import xmpp
import urllib2


MAX_FILENAME_LEN = 200
# TODO: Fix those freaking colors!
# Taken from http://super-productive.com/178
SAFE_COLORS = [
              '0000FF','FF0000','F0F8FF','FAEBD7','00FFFF','7FFFD4','F0FFFF','F5F5DC','FFE4C4','000000',
              'FFEBCD','8A2BE2','A52A2A','DEB887','5F9EA0','7FFF00','D2691E','FF7F50','6495ED','FFF8DC',
              'DC143C','00FFFF','00008B','008B8B','B8860B','A9A9A9','006400','BDB76B','8B008B','556B2F',
              'FF8C00','9932CC','8B0000','E9967A','8FBC8F','483D8B','2F4F4F','00CED1','9400D3','FF1493',
              '00BFFF','696969','1E90FF','B22222','FFFAF0','228B22','FF00FF','DCDCDC','E0E0E0','FFD700',
              'DAA520','808080','008000','ADFF2F','CC5500','FF69B4','CD5C5C','4B0082','FFFFF0','F0E68C',
              'E6E6FA','FFF0F5','7CFC00','FFFACD','ADD8E6','F08080','E0FFFF','FAFAD2','D3D3D3','90EE90',
              'FFB6C1','FFA07A','20B2AA','87CEFA','778899','B0C4DE','FFFFE0','00FF00','32CD32','FAF0E6',
              'FF00FF','800000','66CDAA','0000CD','BA55D3','9370D8','3CB371','7B68EE','00FA9A','48D1CC',
              'C71585','191970','F5FFFA','FFE4E1','FFE4B5','FFDEAD','000080','FDF5E6','808000','6B8E23',
              'FFA500','FF4500','DA70D6','EEE8AA','98FB98','AFEEEE','D87093','FFEFD5','FFDAB9','CD853F',
              'FFC0CB','DDA0DD','B0E0E6','800080','BC8F8F','4169E1','8B4513','FA8072','F4A460','2E8B57',
              'FFF5EE','A0522D','C0C0C0','87CEEB','6A5ACD','708090','FFFAFA','00FF7F','4682B4','D2B48C',
              '008080','D8BFD8','FF6347','40E0D0','EE82EE','F5DEB3','A86363','F5F5F5','FFFF00','9ACD32',
              ]


def get_message_sender_folder(message):
    if message.getType() == 'groupchat':
        return message.getFrom().getStripped() + '.chat'
    return str(message.getFrom())

def get_safe_filename(s):
    s = urllib2.quote(s)
    #keepcharacters = (' ','.','_', '@')
    #s = s.replace('/', '!')
    #s = "".join(c for c in s if c.isalnum() or c in keepcharacters).rstrip()
    if len(s) > MAX_FILENAME_LEN:
        s = s[:200] + hashlib.sha256(s).hexdigest()
    return s

def html_escape(s):
    if s is None:
        return ''
    return cgi.escape(s).replace(' ', '&nbsp;').replace('\n', '<br />')

def convert_timestamp(timestamp):
    time_now = time.strftime('%H:%M:%S')
    if not timestamp:
        return time_now
    yyyy = timestamp[:4]
    mm = timestamp[4:6]
    dd = timestamp[6:8]
    tm = timestamp.partition('T')[-1]
    
    return u'%s %s/%s/%s %s'%(time_now, yyyy, mm, dd, tm)
    

class ChatlogPlugin(plugins.JabberPlugin):
    ''' Performs MUC logging in html format'''
    
    def __init__(self, folder):
        self.folder = folder
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        self.bot_instances = []
        
    def add_bot_instance(self, bot_instance):
        self.bot_instances.append(bot_instance)
    
    def remove_bot_instance(self, bot_instance):
        self.bot_instances.remove(bot_instance)
                    
    def get_current_filename(self, subfolder):
        return os.path.join(subfolder, time.strftime('%Y_%m_%d.html'))
    
    def write_header(self, f):
        f.write('''<html><head><meta http-equiv="content-type" content="text/html; charset=UTF-8"></head><body>''')
                
    def write_message(self, f, message, bot_instance):
        assert isinstance(message, xmpp.Message)
        if self.is_bad_stanza(message):
            self.write_error(f, message)
            return
        text = html_escape(message.getBody())
        subject = html_escape(message.getSubject())
        nick = html_escape(message.getFrom().getResource())
        color = SAFE_COLORS[int(hashlib.sha256(nick.encode('utf-8')).hexdigest()[:6], 16) % len(SAFE_COLORS)]
        message_template = u'''<div class="message" style="color: {text_color}"><font color="#{color}"><font size="2">({timestamp})</font> <b>{nick}:</b></font> <span class="message_text">{text}</span></div>'''
        timestamp = convert_timestamp(message.getTimestamp())
        if subject:
            text += '''<div class="subject"><strong>Subject was changed to: %s</strong></div>''' % subject
        if xmpp.NS_DELAY in message.getProperties():
            text_color = 'grey'
        else:
            text_color = 'black'
        f.write(message_template.format(color=color, timestamp=timestamp, nick=nick, text=text,
                                        text_color=text_color).encode('utf-8'))
        
    def write_presence(self, f, presence, bot_instance):
        assert isinstance(presence, xmpp.Presence)
        if self.is_bad_stanza(presence): 
            self.write_error(f, presence)
            return
        conference = presence.getFrom().getStripped()
        nick = presence.getFrom().getResource()
        msg_html = ['<strong>', html_escape(nick), '</strong>']
        jid = html_escape(presence.getJid())
        if jid:
            msg_html.extend((' (<span style="color: grey">', jid, '</span>)'))
        msg_html.append(' ')
        if presence.getType() == 'unavailable':
            new_nick = html_escape(presence.getNick())
            if new_nick:
                msg_html.extend((' has changed nick to <strong>', new_nick, '</strong>'))
            else:
                msg_html.append('has left')
        else:
            if bot_instance.get_room_user(conference, nick) is not None:
                msg_html.append('has changed status')
            else:
                msg_html.append('has joined the room')
        reason = html_escape(presence.getReason())
        if reason:
            msg_html.extend(('. Reason: <span class="reason">', reason, '</span>'))
        msg_html.append('.')
        msg_html = u''.join(msg_html)
        affiliation = presence.getAffiliation()
        role = presence.getRole()
        show = presence.getShow()
        status = presence.getStatus()
        msg_info = []
        for name, item in (('Affiliation', affiliation), ('Role', role), ('Show', show), ('Status', status)):
            if item is not None:
                msg_info.extend((name, ': <span class="',name,'">&quot;', html_escape(item), '&quot;</span> '))
        msg_info = u''.join(msg_info)
        timestamp = convert_timestamp(presence.getTimestamp())
        presence_template = u'''<div class="presence"></div><font size="2">({timestamp})</font> {msg_html} {msg_info}</div>'''
        f.write(presence_template.format(timestamp=timestamp, msg_html=msg_html, msg_info=msg_info))

        
    def roll_file(self, subfolder=None):
        if subfolder is not None:
            subfolder = os.path.join(self.folder, subfolder)
        else:
            subfolder = self.folder
        if not os.path.isdir(subfolder):
            os.makedirs(subfolder)
        filename = self.get_current_filename(subfolder)
        if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
            with open(filename, 'wb') as f:
                self.write_header(f)
        return filename
    
    @plugins.register_plugin_method
    def process_message(self, message, bot_instance):
        if message.getError() is not None:
            self.process_error(message)
        if self.is_stanza_from_nowhere(message):
            return
        from_ = get_safe_filename(get_message_sender_folder(message))
        filename = self.roll_file(from_)
        with open(filename, 'ab') as f:
            self.write_message(f, message, bot_instance)

    def is_bad_stanza(self, stanza):
        return stanza.getError() is not None or self.is_stanza_from_nowhere(stanza)
    
    def is_stanza_from_nowhere(self, stanza):
        return not stanza.getFrom() or not stanza.getFrom().getStripped()

    @plugins.register_plugin_method
    def process_presence(self, presence, bot_instance):
        if self.is_bad_stanza(presence):
            self.process_error(presence)
        if self.is_stanza_from_nowhere(presence):
            return
        if not xmpp.NS_MUC_USER in presence.getProperties():
            return
        from_ = get_safe_filename(presence.getFrom().getStripped() + '.chat')
        filename = self.roll_file(from_)
        with open(filename, 'ab') as f:
            self.write_presence(f, presence, bot_instance)
            
    def process_error(self, stanza):
        filename = self.roll_file('errors')
        with open(filename, 'ab') as f:
            self.write_error(f, stanza)
        
    def write_error(self, f, stanza):
        f.write((u'<pre style="color: red">%s\n%s</pre>'%(time.asctime(), html_escape(stanza.__str__(fancy=True)))).encode('utf-8'))
        
        
if __name__ == '__main__':
    plugin = ChatlogPlugin('test')