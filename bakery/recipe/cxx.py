#--------------------------------------------------------------------
# bakery.cxx: Modules and Classes for building C++ artifacts.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

from xeno import provide

from ..file import File, FileTask
from ..util import shell, log_for
from ..core import *

#--------------------------------------------------------------------
class Object(FileTask):
    def __init__(self, src, config):
        super().__init__(File.change_ext(src, 'o'))
        self.src = File.as_file(src)
        self.config = config
    
    def run(self):
        log_for(self).info('Building C++: %s' % self.src.relpath())
        shell(self.config.CXX, self.config.CXXFLAGS, '-c', self.src, '-o', self.file)
        return self.file

#--------------------------------------------------------------------
class Executable(FileTask):
    def __init__(self, objects, output, config):
        super().__init__(File.as_file(output))
        self.objects = objects
        self.config = config

    def run(self):
        log_for(self).info('Building executable: %s' % self.file.relpath())
        shell(self.config.CXX, self.config.CXXFLAGS, self.config.LDFLAGS, '-o', self.file, self.objects)
        return self.file

#--------------------------------------------------------------------
class Config:
    def __init__(self):
        self.CXX = 'clang++'
        self.CXXFLAGS = []
        self.LDFLAGS = []

#--------------------------------------------------------------------
class Builder:
    def __init__(self, config):
        self.config = config
    
    def compile(self, src):
        return Object(src, self.config)

    def link(self, objects, output):
        return Executable(objects, output, self.config)

#--------------------------------------------------------------------
@namespace('Recipe::C++')
class BuildModule:
    def __init__(self):
        self.config = Config()
    
    @provide
    def config(self):
        return self.config

    @provide
    def builder(self, config):
        return Builder(config)

