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
    def __init__(self, plugin, function_to_execute, *args, **kwargs):
        super(ThreadedPluginTask, self).__init__()
        self.plugin = plugin
        self.function_to_execute = function_to_execute
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        self.execute_function()

    def execute_function(self):
        return self.function_to_execute(*self.args, **self.kwargs)

    def on_finished(self):
        self.plugin.on_task_finished(self)

class ThreadedPlugin(plugins.JabberPlugin):
    ''' This class is a convenient base for all plugins which expose long-running tasks functionality
    max_tasks is the number of simultaneously running tasks. '''
    max_tasks = plugins.make_config_property('max_tasks', lambda self, val:int(val), default=lambda:-1)

    def __init__(self, config_section, logger=None):
        super(ThreadedPlugin, self).__init__(config_section, logger=logger)
        self.running_tasks = 0
        self.running_tasks_lock = threading.Lock()

    def on_task_finished(self, task):
        self._decrease_running_tasks()

    def _decrease_running_tasks(self):
        with self.running_tasks_lock:
            self.running_tasks -= 1

    def add_task(self, task):
        with self.running_tasks_lock:
            if self.max_tasks >= 0 and self.running_tasks >= self.max_tasks:
                return False
            if not self.bot_instance.add_task(task):
                return False
            # Since running_tasks_lock is taken, we will always decrease running_tasks only after
            # this increase, so running_tasks value would always stay consistent
            self.running_tasks += 1
            return True
