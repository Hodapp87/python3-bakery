#--------------------------------------------------------------------
# bakery.util: Common utility functions.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import multiprocessing_on_dill as multiprocessing
import inspect
import logging
import os
import subprocess

#--------------------------------------------------------------------
def compose(arg, *functions):
    result = arg
    for f in functions:
        result = f(result)
    return result

#--------------------------------------------------------------------
def degenerate(arg):
    if inspect.isgenerator(arg):
        return list(arg)
    else:
        return arg

#--------------------------------------------------------------------
def flat_map(arg, f = lambda x: x):
    if isinstance(arg, (list, tuple)):
        results = []
        for x in arg:
            results.extend(flat_map(x, f))
        return results

    elif isinstance(arg, dict):
        return flat_map(list(arg.values()), f)

    else:
        return [f(arg)]

#--------------------------------------------------------------------
def wide_foreach(arg, f = lambda x: x):
    if isinstance(arg, (list, tuple)):
        for x in arg:
            wide_foreach(x, f)
    elif isinstance(arg, dict):
        for x in arg.values():
            wide_foreach(x, f)
    else:
        f(arg)

#--------------------------------------------------------------------
def wide_map(arg, f = lambda x: x):
    if isinstance(arg, (list, tuple)):
        return [wide_map(x, f) for x in arg]
    elif isinstance(arg, dict):
        return {key: wide_map(value, f) for key, value in arg.items()}
    else:
        return f(arg)

#--------------------------------------------------------------------
def log_for(obj):
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return logger_for_function(obj)
    else:
        return logger_for_class(obj)

#--------------------------------------------------------------------
def logger_for_class(obj):
    return logging.getLogger(name_for_class(obj))

#--------------------------------------------------------------------
def logger_for_function(f):
    return logging.getLogger(name_for_function(f))

#--------------------------------------------------------------------
def name_for_class(obj):
    if inspect.isclass(obj):
        return obj.__module__ + '.' + obj.__qualname__
    else:
        return obj.__module__ + '.' + obj.__class__.__qualname__

#--------------------------------------------------------------------
def name_for_function(f):
    return f.__module__ + '.' + f.__qualname__

#--------------------------------------------------------------------
def shell(*args, check = True):
    log = logger_for_function(shell)
    cmd_line = compose(args,
        lambda x: flat_map(x, degenerate),
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

#--------------------------------------------------------------------
process_pool = multiprocessing.Pool()

#--------------------------------------------------------------------
def get_process_pool():
    return process_pool
    
