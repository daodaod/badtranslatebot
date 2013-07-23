#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import sys
import Queue

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class Task(object):
    def execute(self):
        pass
    
class PoolWorker(StoppableThread):
    def __init__(self, task_queue, exception_handler):
        super(PoolWorker, self).__init__()
        self.task_queue = task_queue
        self.exception_handler = exception_handler
                
    def run(self):
        while not self.stopped():
            try:
                task = self.task_queue.get(timeout=1)
            except Queue.Empty:
                pass
            else:
                try:
                    task.execute()
                except Exception:
                    if self.exception_handler is not None:
                        self.exception_handler(*sys.exc_info())
                    
class TaskPool(object):
    def __init__(self, workers_num, max_task_num, exception_handler=None):
        super(TaskPool, self).__init__()
        self.task_queue = Queue.Queue(maxsize=max_task_num)
        self.exception_handler = exception_handler
        self.workers = [PoolWorker(self.task_queue, self.exception_handler) for _ in xrange(workers_num)]
        [worker.start() for worker in self.workers]
        
    def add_task(self, task):
        '''Adds the task to the queue. May raise Queue.Full'''
        self.task_queue.put_nowait(task)
        
    def join(self):
        for worker in self.workers:
            worker.join()
            
    def stop(self):
        for worker in self.workers:
            worker.stop()
            
            
if __name__ == '__main__':
    pool = TaskPool(workers_num=5, max_task_num=5)
    import time
    class SleepTask(Task):
        def __init__(self, to_sleep, message):
            self.to_sleep = to_sleep
            self.message = message
            
        def execute(self):
            time.sleep(self.to_sleep)
            print "Slept %r seconds and the message is '%s'"%(self.to_sleep, self.message)
            
    pool.add_task(SleepTask(2,"First one"))
    pool.add_task(SleepTask(1, "Second one, but first two"))
    pool.add_task(SleepTask(5, "Sleep sort!"))
    pool.add_task(SleepTask(3, "Cool."))
    pool.stop()
    pool.join()