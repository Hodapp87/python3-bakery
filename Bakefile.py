#--------------------------------------------------------------------
@task
def primes(max = 20000):
    result = []
    for n in range(1, max):
        if all(n % i != 0 for i in range(2, n)):
            result.append(n)
    return result

#--------------------------------------------------------------------
@build()
@require('bakery.recipe.cpp')
class ExampleProgram:
    @setup
    def setup(self, builder):
        builder.config.CXX = 'clang++'
        builder.config.CXXFLAGS.extend([
            '-g',
            '-rdynamic',
            '--std=c++14',
            '-I./demo/include'])

    @provide
    def input_files(self):
        return File.glob('demo/src/*.cpp')

    @temporary
    def objects(self, builder, input_files):
        return [builder.compile(x) for x in input_files]

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
    def build(self, builder, objects):
        executable = builder.link(objects, 'program')
        return executable
