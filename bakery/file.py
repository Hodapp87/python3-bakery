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
import shutil

from .work import Task, Cleanable, Interpolatable, CleanupError
from .log import BuildLog

#--------------------------------------------------------------------
class File(Cleanable, Interpolatable):
    """
        A string wrapper class representing a file on disk.
    """
    def __init__(self, filename):
        self.filename = str(filename)

    @staticmethod
    def glob(*args, **kwargs):
        """ Returns a list of File objects matching the given glob. """
        return [File(f) for f in glob.glob(*args, **kwargs)]

    @staticmethod
    def as_file(obj):
        """
            Used as a filter to ensure that a parameter is a File.
            If a string is provided, it is wrapped as a File, otherwise
            File objects are passed through untouched.
        """
        if isinstance(obj, File):
            return obj
        else:
            return File(obj)

    @staticmethod
    def change_ext(src, dest_ext):
        """
            Used to change the extension of the given string or File object.
            Returns a File object with the extension changed.
        """
        src_basename, src_ext = os.path.splitext(str(src))

        if (dest_ext.startswith('.')):
            return File(src_basename + dest_ext)
        else:
            return File(src_basename + '.' + dest_ext)

    def abspath(self):
        """
            Returns the absolute path of the File as a string, as per
            'os.path.abspath()'.
        """
        return os.path.abspath(os.path.expanduser(self.filename))

    def remove(self):
        """
            Removes the file if it exists, otherwise does nothing.
        """
        if self.exists():
            if os.path.isdir(self.abspath()):
                BuildLog.get(self).task('Deleting directory: %s' % self.relpath())
                shutil.rmtree(self.abspath())
            else:
                BuildLog.get(self).task('Deleting file: %s' % self.relpath())
                os.remove(self.abspath())

    def exists(self):
        """
            Determine if the File exists on disk as per 'os.path.exists()'.
        """
        return os.path.exists(self.abspath())

    def is_dir(self):
        """
            Determine if this File object refers to a directory.
        """
        return os.path.isdir(self.abspath())

    def relpath(self, path = None):
        """
            Gets a path to the file on disk relative to the given path or
            the current directory as per 'os.path.relpath()'.
        """
        if path is None:
            path = os.getcwd()
        return os.path.relpath(self.abspath(), path)
    
    def needs_cleaning(self, recursive = False):
        if self.is_dir() and not recursive:
            raise CleanupError('Won\'t clean directory "%s", use "-R" to enable recursive cleaning.' % self.relpath())
        else:
            return self.exists()

    def clean(self):
        self.remove()
    
    def interp(self):
        return [self.abspath()]

#--------------------------------------------------------------------
class FileTask(Task, Cleanable, Interpolatable):
    """
        Base class for a task that generates a file on disk.
    """
    def __init__(self, file):
        super().__init__(str(file))
        self.file = file

    def is_done(self):
        return self.file.exists()

    def needs_cleaning(self, recursive = False):
        return self.file.needs_cleaning(recursive = recursive)

    def result(self):
        return self.file

    def clean(self):
        self.file.clean()
    
    def interp(self):
        return self.file.interp()

