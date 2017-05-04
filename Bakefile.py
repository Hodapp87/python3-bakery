from bakery import *
from bakery.recipe.cxx import BuildModule

#--------------------------------------------------------------------
@task
def primes(max = 20000):
    result = []
    for n in range(1, max):
        if all(n % i != 0 for i in range(2, n)):
            result.append(n)
    return result

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

    @parallel
    @target
    def parallel_primes(self):
        return [primes() for x in range(10)]

    @target
    def iterative_primes(self):
        return [primes() for x in range(10)]

    @output
    @target
    @default
    def build(self, cxx, objects):
        executable = cxx.link(objects, 'program')
        return executable

#--------------------------------------------------------------------
build(BuildModule(), ExampleProgram())

