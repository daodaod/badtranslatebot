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

    def on_finished(self):
        ''' Always called after task is executed (even if an exception was raised while executing) '''
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
                finally:
                    try:
                        task.on_finished()
                    except Exception:
                        # Normally this should never happen
                        if self.exception_handler is not None:
                            self.exception_handler(*sys.exc_info())

class TaskPool(object):
    def __init__(self, workers_num=0, daemon_threads=True, exception_handler=None):
        super(TaskPool, self).__init__()
        self.task_queue = Queue.Queue()
        self.exception_handler = exception_handler
        self.daemon_threads = daemon_threads
        self.workers = []
        self.resize_workers(workers_num)

    def resize_workers(self, workers_num):
        if workers_num < 0:
            raise ValueError("Workers number can't be negative!")
        self.task_queue.maxsize = max(1, workers_num)  # Don't allow unlimited queues
        if len(self.workers) < workers_num:
            new_workers_num = workers_num - len(self.workers)
            new_workers = [PoolWorker(self.task_queue, self.exception_handler) for _ in xrange(new_workers_num)]
            [worker.setDaemon(self.daemon_threads) for worker in new_workers]
            [worker.start() for worker in new_workers]
            self.workers.extend(new_workers)
        elif len(self.workers) > workers_num:
            to_delete_workers = len(self.workers) - workers_num
            self.workers, deleted_workers = self.workers[:-to_delete_workers], self.workers[-to_delete_workers:]
            [worker.stop() for worker in deleted_workers]


    def add_task(self, task):
        '''Adds the task to the queue. Return True if succeeded, otherwise False'''
        try:
            self.task_queue.put_nowait(task)
        except Queue.Full:
            return False
        else:
            return True

    def join(self):
        for worker in self.workers:
            worker.join()

    def stop(self):
        for worker in self.workers:
            worker.stop()


if __name__ == '__main__':
    pool = TaskPool(workers_num=5, daemon_threads=True)
    import time
    class SleepTask(Task):
        def __init__(self, to_sleep, message):
            self.to_sleep = to_sleep
            self.message = message

        def execute(self):
            time.sleep(self.to_sleep)
            print "Slept %r seconds and the message is '%s'" % (self.to_sleep, self.message)
    pool.resize_workers(0)
    print pool.add_task(SleepTask(2, "First one"))
    print pool.add_task(SleepTask(1, "Second one, but first two"))
    print pool.add_task(SleepTask(5, "Sleep sort!"))
    pool.resize_workers(2)
    print pool.workers
    pool.add_task(SleepTask(3, "Cool."))
    # pool.stop()
    pool.join()
