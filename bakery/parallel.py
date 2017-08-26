#--------------------------------------------------------------------
# bakery.parallel: Implementation of a ParallelTaskQueue
#
# Author: Lain Supe (supelee)
# Date: Tuesday, April 4 2017
#--------------------------------------------------------------------

import multiprocessing_on_dill as multiprocessing
from .work import TaskQueue

#--------------------------------------------------------------------
process_pool = multiprocessing.Pool()

#--------------------------------------------------------------------
def get_process_pool():
    return process_pool

