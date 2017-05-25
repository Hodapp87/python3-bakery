#--------------------------------------------------------------------
# bakery.log: Tools for logging and printing to the console.
#
# Author: Lain Supe (supelee)
# Date: Friday, May 19 2017
#--------------------------------------------------------------------

from termcolor import colored

from .util import *

#--------------------------------------------------------------------
class BuildLog:
    @staticmethod
    def get(obj, log = True):
        return BuildLog(log_for(obj) if log else None)

    def __init__(self, logger):
        self.logger = logger

    def message(self, prefix, msg, colors = (), attrs = (), prefix_colors = (), prefix_attrs = ('bold',)):
        print(colored(prefix, *prefix_colors, attrs = prefix_attrs),
              colored(msg, *colors, attrs = attrs))

    def target(self, msg):
        self.message('====>', msg, prefix_colors = ('magenta',))
        if self.logger:
            self.logger.info('====> %s' % msg)

    def task(self, msg):
        self.message('-->', msg, prefix_colors = ('cyan',))
        if self.logger:
            self.logger.info(msg)

    def error(self, msg):
        self.message('==/==', msg, colors = ('red',), attrs = ('bold',), prefix_colors = ('white', 'on_red'))
        if self.logger:
            self.logger.error(msg)

    def warning(self, msg):
        self.message('-/!\-', msg, prefix_colors = ('yellow',))
        if self.logger:
            self.logger.warn(msg)

    def success(self, msg):
        self.message('====>', msg, prefix_colors = ('green',), attrs = ('bold',))
        if self.logger:
            self.logger.info('====> %s' % msg)

