#--------------------------------------------------------------------
# bakery.util: Common utility functions.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import logging
import os
import subprocess

#--------------------------------------------------------------------
def flat_map(arg, f = lambda x: x):
    for x in arg:
        if isinstance(x, (list, tuple)):
            for y in flat_map(x, f):
                yield f(y)
        else:
            yield f(x)

#--------------------------------------------------------------------
def logger_for_class(obj):
    return logging.getLogger(
        obj.__module__ + '.' + obj.__class__.__name__)

#--------------------------------------------------------------------
def get_logger_for_function(f):
    return logging.getLogger(
        f.__module__ + '.' + f.__name__)

#--------------------------------------------------------------------
def shell(*args, **kwargs):
    log = get_logger_for_function(shell)
    cmd_line = list(flat_map(args, lambda x: str(x)))
    log.info("Executing command: %s" % " ".join(cmd_line))
    subprocess.check_call(cmd_line)

