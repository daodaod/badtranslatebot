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

# http://xmpp.org/extensions/xep-0085.html
CHAT_STATES = ['active', 'composing', 'paused', 'inactive', 'gone']

SAFE_COLORS = ['*000*', '300', '600', '900', 'C00', '*F00*', '*003*', '303', '603', '903',
                'C03', '*F03*', '006', '306', '606', '906', 'C06', 'F06', '009', '309', '609',
                '909', 'C09', 'F09', '00C', '30C', '60C', '90C', 'C0C', 'F0C', '*00F*', '30F',
                '60F', '90F', 'C0F', '*F0F*', '030', '330', '630', '930', 'C30', 'F30', '033',
                '333', '633', '933', 'C33', 'F33', '036', '336', '636', '936', 'C36', 'F36',
                '039', '339', '639', '939', 'C39', 'F39', '03C', '33C', '63C', '93C', 'C3C',
                'F3C', '03F', '33F', '63F', '93F', 'C3F', 'F3F', '060', '360', '660', '960',
                'C60', 'F60', '063', '363', '663', '963', 'C63', 'F63', '066', '366', '666',
                '966', 'C66', 'F66', '069', '369', '669', '969', 'C69', 'F69', '06C', '36C',
                '66C', '96C', 'C6C', 'F6C', '06F', '36F', '66F', '96F', 'C6F', 'F6F']


def get_message_sender_folder(message):
    if message.getType() == 'groupchat':
        return message.getFrom().getStripped() + '.chat'
    return str(message.getFrom())

def get_safe_filename(s):
    s = urllib2.quote(s, safe='')
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
        message_template = (u'''<div class="message" style="color: {text_color}"><font color="#{color}">'''
                            '''<font size="2">({timestamp})</font> <b>{nick}:</b></font> '''
                            '''<span class="message_text">{text}</span>{chat_state}</div>''')
        timestamp = convert_timestamp(message.getTimestamp())
        if subject:
            text += '''<div class="subject"><strong>Subject was changed to: %s</strong></div>''' % subject
        if xmpp.NS_DELAY in message.getProperties():
            text_color = 'grey'
        else:
            text_color = 'black'
        chat_state = []
        for state in CHAT_STATES:
            if message.getTag(state):
                chat_state.append(state)
        if text or not chat_state:
            chat_state = ''
        else:
            chat_state = '<font style="color:green">Conversation state: <span class="chat_state">'+','.join(chat_state)+'</span></font>'
        f.write(message_template.format(color=color, timestamp=timestamp, nick=nick, text=text,
                                        text_color=text_color, chat_state=chat_state).encode('utf-8'))
        
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
        print [msg_html, msg_info]
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