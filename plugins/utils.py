'''
Created on 11.08.2013

@author: H
'''

import re

def split_by_nickname(text, nickname, make_lower=False):
    # The idea is to catch nickname with non-alphabetic character after it.
    if make_lower:
        text = text.lower()
    parts = re.split(r'(%s(?:\W|$)|\w+)' % re.escape(nickname), text,
                     flags=re.UNICODE | re.IGNORECASE)
    nickname_lower = nickname.lower()
    for i, part in enumerate(parts):
        part_lower = part.lower()
        # Maybe it's the case when we captured non-alphabetic character?
        if len(part_lower) == len(nickname_lower) + 1:
            if part_lower[:-1] == nickname_lower and not part_lower[-1].isalpha():
                # Append it to the next chunk.
                part, to_append = part[:-1], part[-1:]
                parts[i] = part
                parts[i + 1] = to_append + parts[i + 1]
    return parts

def remove_nickname_from_list(parts, nickname, limit=None):
    nickname_lower = nickname.lower()
    if limit is None:
        limit = len(parts)
    for (i, part), _ in zip(enumerate(parts), range(limit)):
        if part.lower() == nickname_lower:
            parts[i] = ' '
            parts[i - 1] = parts[i + 1] = ''
    return ''.join(parts).strip()

def remove_nickname(text, nickname, startswith_nick=False):
    limit = 3 if startswith_nick else None
    return remove_nickname_from_list(split_by_nickname(text, nickname), nickname, limit=limit)

def is_message_for_me(text, nickname, startswith_nick=False):
    ''' Return text with nickname removed if nickname is present. Return None otherwise. '''
    new_text = remove_nickname(text, nickname, startswith_nick=startswith_nick)
    return new_text if (new_text != text) else None

if __name__ == '__main__':

    # parts = split_by_nickname('Hey, Johny-John', 'John', False)
    # print parts
    # print split_by_nickname('Hey, John!', 'John', max_split=1)
    # print remove_nickname("Hey         ho!  Yo", "ho", startswith_nick=True)
    print [remove_nickname("       ho!  Yo", "ho", startswith_nick=True)]
