#--------------------------------------------------------------------
# bakery.c: Modules and Classes for building C artifacts.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

from xeno import provide

from ..core import *
from ..file import File, FileTask
from ..log import BuildLog
from ..work import shell

#--------------------------------------------------------------------
class ObjectMaker(FileTask):
    def __init__(self, src, config):
        super().__init__(File.change_ext(src, 'o'))
        self.src = File.as_file(src)
        self.config = config

    def run(self):
        BuildLog.get(self).task('Compiling C: %s' % self.src.relpath())
        shell(self.config.CC, self.config.CFLAGS, '-c', self.src, '-o', self.file)
        return self.file

#--------------------------------------------------------------------
class ExecutableMaker(FileTask):
    def __init__(self, objects, output, config):
        super().__init__(File.as_file(output))
        self.objects = objects
        self.config = config

    def run(self):
        BuildLog.get(self).task('Linking executable: %s' % self.file.relpath())
        shell(self.config.CC, self.config.CFLAGS, self.config.LDFLAGS, '-o', self.file, self.objects)
        return self.file

#--------------------------------------------------------------------
class Config:
    def __init__(self):
        self.CC = 'clang'
        self.CFLAGS = []
        self.LDFLAGS = []

#--------------------------------------------------------------------
class Builder:
    def __init__(self, config):
        self.config = config

    def compile(self, src):
        return ObjectMaker(src, self.config)

    def link(self, objects, output):
        return ExecutableMaker(objects, output, self.config)

#--------------------------------------------------------------------
@namespace('recipe/c')
class Module:
    def __init__(self):
        self.config = Config()

    @provide
    def config(self):
        return self.config

    @provide
    def builder(self, config):
        return Builder(config)

