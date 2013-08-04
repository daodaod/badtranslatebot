#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plugins
import threadpool
import threading

class ThreadedPluginTask(threadpool.Task):
    ''' This class is used with ThreadedPlugin. First call the constructor to define callbacks, then
    call set_args_kwargs to set arguments. On execute execute_function will be run with these args and return
    value will be passed to result_callback, which by default is plugin.on_task_result.
    '''
    def __init__(self, plugin, bot_instance, message, execute_function,
                 result_callback=None, finish_callback=None):
        self.plugin = plugin
        self.bot_instance = bot_instance
        self.message = message
        self.execute_function = execute_function
        self.result_callback = result_callback or self.plugin.on_task_result
        self.finish_callback = finish_callback or self.plugin.on_task_finished
        self.args = []
        self.kwargs = {}
        super(ThreadedPluginTask, self).__init__()

    def set_args_kwargs(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        result = self.execute_function(*self.args, **self.kwargs)
        self.result_callback(self, result)

    def on_finished(self):
        self.finish_callback(self)

class ThreadedPlugin(plugins.JabberPlugin):
    ''' This class is a convenient base for all plugins which expose long-running tasks functionality
    max_tasks is the number of simultaneously running tasks. '''

    def __init__(self, max_tasks):
        self.max_tasks = max_tasks
        self.running_tasks = 0
        self.running_tasks_lock = threading.Lock()
        super(ThreadedPlugin, self).__init__()


    def on_task_result(self, task, *args, **kwargs):
        pass

    def on_task_finished(self, task):
        self._decrease_running_tasks()

    def _decrease_running_tasks(self):
        with self.running_tasks_lock:
            self.running_tasks -= 1

    def add_task(self, task, bot_instance):
        with self.running_tasks_lock:
            if self.running_tasks >= self.max_tasks:
                return False
            if not bot_instance.add_task(task):
                return False
            # Since running_tasks_lock is taken, we will always decrease running_tasks only after
            # this increase, so running_tasks value would always stay consistent
            self.running_tasks += 1
            return True
