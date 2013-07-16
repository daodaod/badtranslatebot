#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import urllib
import urllib2
import json
import random
import time

LANGUAGES = [u'el', u'gu', u'en', u'ga', u'af', u'vi', u'is', u'it', u'iw',
             u'sv', u'cs', u'cy', u'ar', u'bg', u'et', u'eu', u'eo', u'gl',
             u'id', u'es', u'ru', u'az', u'nl', u'pt', u'la', u'lo', u'tr',
             u'tl', u'lv', u'lt', u'th', u'ro', u'ca', u'pl', u'ta', u'yi',
             u'be', u'fr', u'hy', u'mt', u'uk', u'sl', u'hr', u'bn', u'de',
             u'ht', u'hu', u'fa', u'hi', u'fi', u'da', u'ja', u'ka', u'te',
             u'zh-TW', u'sq', u'no', u'ko', u'kn', u'mk', u'ur', u'sk',
             u'zh-CN', u'ms', u'sr', u'sw']

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept-Charset': 'utf-8' }

def translate(word, tl, sl=None, timeout=30):
    """
    Translate, using google translate.
    
    word - String to be translated
    tl - Language to be translated on
    sl - Language of source string `word`
    
    Result: unicode string
    """
    url = "http://translate.google.com/translate_a/t?"
    list_of_params = {'client': 't', 
                      'hl': 'en',
                      'multires': '0',
                      'text': word.encode('utf-8'),
                      'tl': tl.encode('utf-8')}  
    if sl is not None:
        list_of_params.update(sl = sl.encode('utf-8'))
    request = urllib2.Request(url + urllib.urlencode(list_of_params),
                              headers=HEADERS)
    result = urllib2.urlopen(request, timeout=timeout).read()
    # Replace ,,,, sequences with ,null,null,null,null, because that's 
    # allowed in javascript, but not in json
    fixed_json = re.sub(r',{2,}', (lambda m:'null'.join(m.group(0))), result)
    fixed_json = fixed_json.replace(',]', ']')  
    data = json.loads(fixed_json)
    result =' '.join(trans[0].decode('utf-8') for trans in data[4])
    # Remove whitespace before punctuation
    result = re.sub(r'\s+([,\.!?\-\(\)\+\=\*])',r'\1', result)
    result = re.sub(r'^\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'[ ]+', ' ', result, flags=re.MULTILINE)
    return result



def bad_translate(word, sl='ru', iterations=20, iter_sleep=0.3,
                  languages=LANGUAGES, request_timeout=30):
    """
    Translate string from one language to another and back `iterations` times
    
    word - String to be translated
    sl - Language of source string `word`
    `iterations` - number of times string will be translated back and forth
    `iter_sleep` - time to sleepbetween translations in order not to abuse google servers
    
    Result: unicode string
    """
    for _ in xrange(iterations):
        while True:
            lang = random.choice(LANGUAGES)
            if lang == sl and len(languages) != 1:
                continue
            break
        foreign_word = translate(word, lang, sl)
        new_word = translate(foreign_word, sl, lang, request_timeout)
        time.sleep(iter_sleep)
        word = new_word
    return new_word

def test():
    word = u"""Everything was almost perfect?\nEverything fell into place."""
    sl = 'en'
    print bad_translate(word, sl, iterations=1)

# I added this stuff in another branch

# Done, merging the branch back
if __name__ == '__main__':
    test()
