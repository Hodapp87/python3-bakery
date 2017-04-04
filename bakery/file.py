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

from .util import logger_for_class

#--------------------------------------------------------------------
class File:
    def __init__(self, filename):
        self.log = logger_for_class(self)
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
    
    def make(self):
        pass

    def build(self):
        if not self.exists():
            self.make()
        if not self.exists():
            raise BuildError('Required file does not exist or was not created: %s' % str(self))
            

    def remove(self):
        if self.exists():
            self.log.warning('Deleting file: %s' % self.abspath())
            os.remove(self.abspath())

    def exists(self):
        return os.path.exists(self.abspath())

    def relpath(self, path = None):
        if path is None:
            path = os.getcwd()
        return os.path.relpath(self.abspath(), path)

    def __str__(self):
        return self.abspath()

