#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bot_command import Command, command_names
import random

class TestCommand(Command):
    @command_names('test', u'тест')
    def say_hello(self, command, args, **kwargs):
        return "Test, '%s'" % args


    @command_names(u'выбор', u'выбери', u'choose')
    def choose_random(self, command, args, **kwargs):
        for sep in ['\n', u' или ', ';', ',']:
            if sep in args:
                args = args.split(sep)
                break
        else:
            args = ''
        args = [arg for arg in args if arg.strip()]
        if not args:
            return u'Не из чего выбирать.'
        return random.choice(args).strip()
