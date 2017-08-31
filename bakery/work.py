#--------------------------------------------------------------------
# bakery.task: Deferred methods and concurrent task queues.
#
# Author: Lain Supe (supelee)
# Date: Tuesday, April 4 2017
#--------------------------------------------------------------------

import functools
import subprocess
from .util import *

#--------------------------------------------------------------------
class InterpolationError(BuildError):
    pass

#--------------------------------------------------------------------
class WorkflowError(BuildError):
    pass

#--------------------------------------------------------------------
class CleanupError(BuildError):
    pass

#--------------------------------------------------------------------
class Actionable:
    @staticmethod
    def is_actionable(obj):
        # Improvement: figure out if a function passed this method
        # is nullary and allow it to be 'actionable'.
        return (has_method(obj, 'run') and
                has_method(obj, 'is_done') and
                has_method(obj, 'result'))

    @staticmethod
    def is_complete(obj):
        # Improvement: figure out if we are passed a function and
        # return false.
        return obj.is_done()

    def is_done(self):
        return False

    def run(self):
        raise NotImplementedError()

    def __call__(self):
        return self.run()

    def result(self):
        return None

#--------------------------------------------------------------------
class Cleanable:
    @staticmethod
    def is_cleanable(obj):
        return (has_method(obj, 'clean') and
                has_method(obj, 'needs_cleaning'))
    
    def needs_cleaning(self, recursive = False):
        return True

    def clean(self):
        raise NotImplementedError()

#--------------------------------------------------------------------
class Interpolatable:
    @staticmethod
    def is_raw(arg):
        return isinstance(arg, (
            int,
            str,
            float
        ))

    @staticmethod
    def interpolate(arg):
        if isinstance(arg, Interpolatable):
            return [Interpolatable.interpolate(x) for x in arg.interp()]
        elif Interpolatable.is_raw(arg):
            return [arg]
        else:
            raise InterpolationError("Cannot interpolate object of type '%s'." % (
                arg.__class__))

    def interp(self):
        raise NotImplementedError()

    def __str__(self):
        return ''.join(flat_map(Interpolatable.interpolate(self)))

#--------------------------------------------------------------------
class Task(Actionable):
    def __init__(self, name = None):
        self.name = name

#--------------------------------------------------------------------
class TaskQueue(Task, Cleanable, Interpolatable):
    def __init__(self, name, tasks = None):
        super().__init__(name)
        self._result = None
        if tasks is not None:
            self.queue = tasks
        else:
            self.queue = []
    
    def is_empty(self):
        return len(self.queue) == 0

    def append(self, task):
        self.queue.append(task)

    def extend(self, tasks):
        self.queue.extend(tasks)

    def breakdown(self):
        return self.queue

    def run(self):
        results = [task() for task in self.queue if not Actionable.is_complete(task)]
        self._result = results
        return results

    def clean(self):
        for task in self.queue:
            if isinstance(task, Cleanable):
                task.clean()

    def result(self):
        return self._result

    def is_done(self):
        return all(Actionable.is_complete(task) for task in self.queue)

    def needs_cleaning(self, recursive = False):
        return any(task.needs_cleaning(recursive = recursive)
            for task in self.queue
            if Cleanable.is_cleanable(task))

    def __bool__(self):
        return bool(self.queue)

    def interp(self):
        if not self._result:
            raise WorkflowError('Cannot interpolate TaskQueue until it has been evaluated.')
        return self._result

#--------------------------------------------------------------------
class ParallelTaskQueue(TaskQueue):
    def __init__(self, name, process_pool, tasks = None):
        super().__init__(name, tasks = tasks)
        self.process_pool = process_pool

    def run(self):
        results = self.process_pool.map(lambda x: x(),
                [task for task in self.queue if not Actionable.is_complete(task)])
        self._result = results
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

#--------------------------------------------------------------------
def shell(*args, check = True):
    log = logger_for_function(shell)
    cmd_line = compose(args,
        lambda x: flat_map(x, degenerate),
        lambda x: flat_map(x, Interpolatable.interpolate),
        lambda x: flat_map(x, lambda x: str(x)))
    log.info("Executing command: %s" % " ".join(cmd_line))

    try:
        subprocess.check_call(cmd_line)
        return 0

    except Exception as e:
        if check:
            raise e
        else:
            return e.returncode

