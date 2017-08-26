#--------------------------------------------------------------------
# bakery.log: Tools for logging and printing to the console.
#
# Author: Lain Supe (supelee)
# Date: Friday, May 19 2017
#--------------------------------------------------------------------

from termcolor import colored
import multiprocessing_on_dill as multiprocessing
from .util import *

#--------------------------------------------------------------------
log_lock = multiprocessing.Lock()

#--------------------------------------------------------------------
class BuildLog:
    @staticmethod
    def get(obj, log = False):
        return BuildLog(log_for(obj) if log else None)

    def __init__(self, logger):
        self.logger = logger

    def message(self, prefix, msg, colors = (), attrs = (), prefix_colors = (), prefix_attrs = ('bold',)):
        print(colored(prefix, *prefix_colors, attrs = prefix_attrs),
              colored(msg, *colors, attrs = attrs))

    def target(self, msg):
        with log_lock:
            self.message('====>', msg, prefix_colors = ('magenta',))
            if self.logger:
                self.logger.info('====> %s' % msg)

    def task(self, msg):
        with log_lock:
            self.message('-->', msg, prefix_colors = ('cyan',))
            if self.logger:
                self.logger.info(msg)

    def error(self, msg):
        with log_lock:
            self.message('[ERROR]', msg, colors = ('red',), attrs = ('bold',), prefix_colors = ('white', 'on_red'))
            if self.logger:
                self.logger.error(msg)

    def warning(self, msg):
        with log_lock:
            self.message('[WARNING]', msg, prefix_colors = ('yellow',))
            if self.logger:
                self.logger.warn(msg)

    def success(self, msg):
        with log_lock:
            self.message('====>', msg, prefix_colors = ('green',), attrs = ('bold',))
            if self.logger:
                self.logger.info('====> %s' % msg)

