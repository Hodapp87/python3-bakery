#--------------------------------------------------------------------
# bakery.os: Recipes for OS and filesystem related tasks
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import shutil

from xeno import provide, singleton

from ..core import *
from ..file import File, FileTask
from ..log import BuildLog

#--------------------------------------------------------------------
class DirectoryMaker(FileTask):
    def __init__(self, path):
        super().__init__(File.as_file(path))

    def run(self):
        if self.file.exists() and not self.file.is_dir():
            raise BuildError('File "%s" already exists and is not a directory.' % self.file.relpath())
        elif not self.file.exists():
            BuildLog.get(self).task('Making directory: %s' % self.file.relpath())
        else:
            BuildLog.get(self).message('Directory exists: %s' % self.file.relpath())

        return self.file

#--------------------------------------------------------------------
class Builder:
    def makedirs(self, path):
        return DirectoryMaker(path)

#--------------------------------------------------------------------
@namespace('recipe/os')
class Module:
    @provide
    @singleton
    def builder(self):
        return Builder()

