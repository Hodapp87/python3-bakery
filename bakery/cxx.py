#--------------------------------------------------------------------
# bakery.cxx: Modules and Classes for building C++ artifacts.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

from xeno import provide

from .file import File
from .util import shell, logger_for_class
from .core import *

#--------------------------------------------------------------------
class ObjectFile(File):
    def __init__(self, src, config):
        super().__init__(File.change_ext(src, 'o'))
        self.log = logger_for_class(self)
        self.src = File.as_file(src)
        self.config = config
    
    def make(self):
        self.log.info('Building C++: %s' % self.src.relpath())
        shell(self.config.CXX, self.config.CXXFLAGS, '-c', self.src, '-o', self)

#--------------------------------------------------------------------
class Executable(File):
    def __init__(self, objects, output, config):
        super().__init__(output)
        self.objects = objects
        self.log = logger_for_class(self)
        self.config = config

    def make(self):
        File.build_all(self.objects)
        self.log.info('Building executable: %s' % self.relpath())
        shell(self.config.CXX, '-o', self, self.objects)

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
        return ObjectFile(src, self.config)

    def link(self, objects, output):
        return Executable(objects, output, self.config)

#--------------------------------------------------------------------
class BuildModule:
    def __init__(self):
        self.config = Config()
    
    @provide
    def cxx_config(self):
        return self.config

    @provide
    def cxx(self, cxx_config):
        return Builder(cxx_config)

