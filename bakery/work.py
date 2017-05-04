#--------------------------------------------------------------------
# bakery.task: Deferred methods and concurrent task queues.
#
# Author: Lain Supe (supelee)
# Date: Tuesday, April 4 2017
#--------------------------------------------------------------------

import functools
import time

from .util import *

#--------------------------------------------------------------------
class Cleanable:
    def cleanup(self):
        raise NotImplementedError()

#--------------------------------------------------------------------
class Breakable:
    def breakdown(self):
        raise NotImplementedError()

#--------------------------------------------------------------------
class Task():
    def __init__(self, name = None):
        self.name = name

    def run(self):
        return None

#--------------------------------------------------------------------
class TaskQueue(Task, Breakable, Cleanable):
    def __init__(self, name, tasks = None):
        super().__init__(name)
        if tasks is not None:
            self.queue = tasks

    def append(self, task):
        self.queue.append(task)

    def extend(self, tasks):
        self.queue.extend(tasks)

    def breakdown(self):
        return self.queue

    def run(self):
        results = [task.run() for task in self.queue]
        return results

    def cleanup(self):
        for task in self.queue:
            if isinstance(task, Cleanable):
                task.cleanup()

    def __bool__(self):
        return bool(self.queue)

#--------------------------------------------------------------------
class ParallelTaskQueue(TaskQueue):
    def __init__(self, name, tasks = None):
        super().__init__(name, tasks = tasks)

    def run(self):
        results = get_process_pool().map(lambda x: x.run(), self.queue)
        return results

#--------------------------------------------------------------------
class DeferredCallTask(Task):
    def __init__(self, f, *args, **kwargs):
        super().__init__(name_for_function(f))
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def run(self):
        return self.f(*self.args, **self.kwargs)

#--------------------------------------------------------------------
def task(f):
    @functools.wraps(f)
    def task_encap_wrapper(*args, **kwargs):
        return DeferredCallTask(f, *args, **kwargs)
    return task_encap_wrapper

