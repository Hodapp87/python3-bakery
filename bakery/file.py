#--------------------------------------------------------------------
# bakery.file: Utilities for operating with files and preventing
#              unneeded work.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import functools
import glob
import logging
import os

from .work import Task, Breakable, Cleanable
from .util import log_for

#--------------------------------------------------------------------
class File(Cleanable):
    def __init__(self, filename):
        self.filename = str(filename)
    
    @staticmethod
    def glob(*args, **kwargs):
        return [File(f) for f in glob.glob(*args, **kwargs)]

    @staticmethod
    def as_file(obj):
        if isinstance(obj, File):
            return obj
        else:
            return File(obj)

    @staticmethod
    def change_ext(src, dest_ext):
        src_basename, src_ext = os.path.splitext(str(src))

        if (dest_ext.startswith('.')):
            return File(src_basename + dest_ext)
        else:
            return File(src_basename + '.' + dest_ext)

    @staticmethod
    def build_all(files):
        return [File.as_file(file).build() for file in files]

    def abspath(self):
        return os.path.abspath(os.path.expanduser(self.filename))
    
    def remove(self):
        if self.exists():
            log_for(self).warning('Deleting file: %s' % self.abspath())
            os.remove(self.abspath())

    def exists(self):
        return os.path.exists(self.abspath())

    def relpath(self, path = None):
        if path is None:
            path = os.getcwd()
        return os.path.relpath(self.abspath(), path)

    def cleanup(self):
        self.remove()

    def __str__(self):
        return self.abspath()

#--------------------------------------------------------------------
class FileTask(Task, Breakable, Cleanable):
    def __init__(self, file):
        super().__init__(str(file))
        self.file = file
        
    def breakdown(self):
        return self.file

    def cleanup(self):
        self.file.cleanup()

    def __str__(self):
        return self.file.abspath()

