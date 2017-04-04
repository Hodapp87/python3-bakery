#--------------------------------------------------------------------
# bakery: A build system built atop xeno
#
# Author: Lain Supe (supelee)
# Date: Wednesday March 22, 2017
#--------------------------------------------------------------------

from bakery import *
from bakery.file import File
from bakery.cxx import BuildModule

#--------------------------------------------------------------------
class ExampleProgram:
    @setup
    def setup(self, cxx):
        cxx.config.CXX = 'clang++'
        cxx.config.CXXFLAGS.extend([
            '-g',
            '-rdynamic',
            '--std=c++14',
            '-I./demo/include'])

    @provide
    def input_files(self):
        return File.glob('demo/src/*.cpp')
    
    @temporary
    def objects(self, cxx, input_files):
        return [cxx.compile(x) for x in input_files]

    @output
    @target
    def build(self, cxx, objects):
        executable = cxx.link(objects, 'program')
        return executable

#--------------------------------------------------------------------
if __name__ == '__main__':
    build(BuildModule(), ExampleProgram())

