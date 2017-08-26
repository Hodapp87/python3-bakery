# Bakery: A warm fluffy Python build system

Bakery is a tree based build system built atop the
[Xeno](https://github.com/lainproliant/python3-xeno) injection framework.
Bakery allows you to define the structure and flow of your build process using
plain Python code.  Bakery mixes the ease of use of Makefiles with the power and
expressiveness of the Python language.

Bakery works with the concept of *build modules*, the first of which is the
*build module* that defines your build process.  Bakery also comes with a growing
set of *recipe modules* that contain targets and resources that can be mixed in
to your *build modules* providing tools for interacting with operating systems,
language compilers, setup tools, and more.  Bakery currently ships with the
following *recipe modules*:

- `recipe/ccp`: Build tools for C++
- `recipe/c`: Build tools for C
- `recipe/os`: Build tools for managing the building and cleanup of files,
    directories, and other OS level resources in your *build module*.

### Note
Bakery is still in early development.  There may be some rough edges or major
bugs.  You are encouraged to try it out now and have fun, but keep in mind that
this is a living project and there's plenty more to come!

# Installation

Installation is simple. With python3-pip, do the following:

```
$ sudo pip install -e .
```

Or, to install the latest version available on PyPI:

```
$ sudo pip install bakery-build
```

Bakery is now available via the `bake` command:

```
$ bake
```

# Usage
The first step to using Bakery is to create a `Bakefile.py` in your project.
This is a Python script that is executed via the `bake` command and contains
your *build module* definition.  This module establishes the setup methods,
inputs, outputs, temporary resources and targets that are needed to build your
project.

Via Xeno, dependencies are declared via the parameters provided to each
method.  Each target, input, output, and temporary resource may return an
*Actionable* object: this is either a nullary function or an object which
implements `bakery.work.Actionable` defining a `run()` and an `is_done()`
method.  When *Actionable* objects are returned this way, Bakery uses the
dependency tree to determine in what order to execute tasks.  Bakery can also
parallelize tasks that are not dependent on each other, either on a per-resource
basis via the `@parallel` resource annotation or at the build resolution level
via the `-P/--parallel` command line switch.  Bakery will automatically spawn
processes equal to the number of processors available to the system, and can do
some cool stuff via
[`multiprocessing_on_dill`](https://pypi.python.org/pypi/multiprocessing_on_dill),
allowing nested classes, functions, and closures to be used in your
parallelized build code.

## Example

This simple example defines a `Bakefile.py` for a simple C project containing a
number of source files which are linked into a resulting executable.  Bakery
uses `clang` by defualt, this can be overridden by setting `builder.CC`.

```
@build
@require('bakery.recipe.c')
class ExampleProgram:
	@setup
	def setup(self, builder):
		builder.CFLAGS.extend([
			'-I./include'
		])	

	@provide
	def input_files(self):
		return File.glob('src/*.c')
	
	@temporary
	@parllel
	def objects(self, builder, input_files):
		return (builder.compile(x) for x in input_files)

	@output
	@default
	def build(self, builder, objects):
		return builder.link(objects, 'program')
```

In the above example, the following Bakery patterns are used:

- `@build` wraps the module so that it is evaluated by Bakery as a build module.
    More than one module may be decorated with `@build`, but no more than one
    target may be marked as `@default` among them.

- `@require` imports the module `bakery.recipe.c` and imports it's namespace
    `recipe/c` as a required namespace of your build module.  `@require` can
    also be provided with a class name which will be imported and used, allowing
    you to mix your own build modules into your main module.

- `@setup` marks a method as a setup method to be run before building any
    targets.  Multiple methods across all modules may be declared as setup
    methods, but they are not guaranteed to be executed in any predictable order
    so they should not depend on side-effects of each other.

- `@provide` is an annotation from
    [Xeno](https://github.com/lainproliant/python3-xeno), marking the given
    method as a named resource that can be injected into other resources (and
    build targets) via their parameter names.

- `@temporary` implies that the resource represents a temporary output that is
    used to build something else, e.g. the list of static object files used to
    build a resulting executable.  Resources marked as `@temporary` should
    (but are not required to) return a `Cleanable` object or structure
    containing `Cleanable` objects which will be cleaned when the build process
    is complete.  This keeps your project from being cluttered by unneeded
    temporary files once your build completes.

- `@parallel` indicates that the resource consists of components that can be
    built in parallel.  In this case, it indicates that each of the `*.c` source
    files can be built into a resulting `*.o` file in parallel.  Bakery will
    allocate a process per CPU core to complete the execution of a set of
    parallel tasks.  Note that Bakery can also perform parallel builds of tasks
    without `@parallel` via the `-P/--parallel` switch to `bake`, which will
    build top level resource tasks in parallel as much as possible to satisfy
    all dependencies.

- `@output` marks a given item as an output that can be cleaned. Any resource
    that represents an action that can be reverted, such as the creation of a
    file or record, can be flagged as `@output`.  `@output` methods should
    return objects that are `Cleanable` and `Actionable` to facilitate this.
    Any targets specified when running `bake -c` to clean will have their
    output's cleaned instead of run.

- `@default` marks the method as a valid nameable target and the default target
    to be executed when no other targets are specified.

### Note
To make the most out of Bakery, you should first read up on
[Xeno](https://github.com/lainproliant/python3-xeno).  *Build modules* in Bakery
are Xeno modules as well, allowing you to require and use resources defined in
other Xeno modules, such as the runtime parts of your Xeno-based project.

