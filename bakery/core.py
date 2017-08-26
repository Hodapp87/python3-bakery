#--------------------------------------------------------------------
# bakery.core: Core modules and features of the Bakery build system.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import argparse
import collections
import inspect
import functools
import logging
import os
import sys
import xeno

from .evaluate import *
from .util import *
from .file import *
from .work import *
from .log import *
from .error import *
from .parallel import get_process_pool

#--------------------------------------------------------------------
def _decorate(tag, f):
    """
        Decorates the given function by adding a xeno attribute with
        the given name prepended by 'bakery.'.
    """
    attrs = xeno.MethodAttributes.for_method(f, write = True)
    attrs.put('bakery.' + tag)
    return f

#--------------------------------------------------------------------
class Config:
    """
        Describes the configuration options that can be passed to the
        'bake' command line tool.
    """
    def __init__(self):
        self.debug = False
        self.target = None
        self.clean = False
        self.parallel = False
        self.recursive_clean = False

    def get_arg_parser(self):
        parser = argparse.ArgumentParser(description = 'Execute targets in bakefiles.')
        parser.add_argument('targets', metavar='TARGET', nargs='*', default=None)
        parser.add_argument('-D', '--debug', action='store_true')
        parser.add_argument('-c', '--clean', action='store_true')
        parser.add_argument('-p', '--parallel', action='store_true')
        parser.add_argument('-R', '--recursive-clean', action='store_true')
        parser.add_argument('-b', '--bakefile')
        return parser

    def is_debug(self):
        return int(os.environ.get('BAKERY_DEBUG', "0")) or self.debug

    def is_cleaning(self):
        return self.clean

    def is_recursive_clean_enabled(self):
        return self.recursive_clean

    def parse_args(self):
        self.get_arg_parser().parse_args(namespace = self)
        return self

#--------------------------------------------------------------------
class TaskDeciderBase(EvaluationDecider):
    """
        A base class providing methods for use by other Task focused
        EvaluationDecider subclasses.
    """
    def get_singleton(self, injector, target):
        """
            Resolve the given target as a singleton from the injector,
            or return None if the target resolved is not a singleton.
            If the target is resolved as a singleton, unbind it so
            that its possibly modified dependencies may be re-injected
            post-build.

            For example, the singleton 'A' may depend on 'B' and 'C'.
            During the build process, 'B' and 'C' resolve to Task
            objects and are executed, with the results being provided
            as singletons in the injector instead of the Task objects.
            Unbinding 'A' allows these task results to be injected
            into 'A' post-build while still expressing the tasks
            'B' and 'C' as dependencies for evaluation.
        """
        attrs = injector.get_resource_attributes(target)
        if attrs.check('singleton'):
            singleton = injector.require(target)
            injector.unbind_singleton(target)
            return singleton
        else:
            return None

    def get_actionable(self, injector, target):
        """
            Fetch the given target from the injector if it is an
            actionable singleton, otherwise return None.
        """
        singleton = self.get_singleton(injector, target)
        if singleton and Actionable.is_actionable(singleton):
            return singleton
        else:
            return None

    def get_cleanable(self, injector, target):
        """
            Fetch the given target from the injector if it is a
            cleanable singleton, otherwise return None.
        """
        singleton = self.get_singleton(injector, target)
        if singleton and Cleanable.is_cleanable(singleton):
            return singleton
        else:
            return None

    def is_temp(self, injector, target):
        """
            Determine if the given target is flagged as temporary.
        """
        attrs = injector.get_resource_attributes(target)
        return attrs.check('bakery.@temporary')

#--------------------------------------------------------------------
class BuildTaskDecider(TaskDeciderBase):
    def get_evaluation_set(self, injector, target, higher_eval_set = None):
        task = self.get_actionable(injector, target)
        if not task or task.is_done() or (self.is_temp(injector, target) and not higher_eval_set):
            eval_set = higher_eval_set or set()
        else:
            eval_set = {target} | (higher_eval_set or set())
        
        for dep in injector.get_dependencies(target):
            eval_set |= self.get_evaluation_set(injector, dep, eval_set)

        return eval_set

    def evaluate(self, injector, target):
        BuildLog.get(self).target('Building target \'%s\'...' % target)
        result = injector.require(target)()
        injector.provide(target, result, is_singleton = True)
        return result

#--------------------------------------------------------------------
class CleanupTaskDecider(TaskDeciderBase):
    def __init__(self, config):
        self.config = config

    def get_evaluation_set(self, injector, target, higher_eval_set = None):
        cleanable = self.get_cleanable(injector, target)
        if not cleanable or not cleanable.needs_cleaning(self.config.is_recursive_clean_enabled()):
            eval_set = higher_eval_set or set()
        else:
            eval_set = {target} | (higher_eval_set or set())

        for dep in injector.get_dependencies(target):
            eval_set |= self.get_evaluation_set(injector, dep, eval_set)

        return eval_set

    def evaluate(self, injector, target):
        BuildLog.get(self).target('Cleaning target \'%s\'...' % target)
        injector.require(target).clean()

#--------------------------------------------------------------------
class Build:
    """
        Implementation of the main build system.  This class is used
        to decorate a module into a build module by flagging its
        resources as targets.  The Build is then provided with a
        Config object specifying arguments to the 'bake' command
        including a list of targets to be built and whether or not
        to clean.
    """
    global_config = Config()
    build_count = 0

    def __init__(self, config = global_config):
        self.outputs = []
        self.targets = set()
        self.temp_outputs = []
        self.setup_resources = []
        self.default_target = None
        self.config = config
        self.modules = []

    @xeno.provide
    @xeno.singleton
    @xeno.named('~build')
    def get_build(self):
        return self

    @xeno.provide
    @xeno.singleton
    @xeno.named('~config')
    def config(self):
        return self.config

    def _generic_task_func_wrapper(self, f, decorator_name,
                                   task_callback = lambda x: None):
        def dispatch_result(result):
            if Actionable.is_actionable(result):
                task_callback(result)
            return result

        @functools.wraps(f)
        def generic_wrapper(mod_self, *args, **kwargs):
            obj = f(mod_self, *args, **kwargs)
            return wide_map(obj, dispatch_result)
        
        return _decorate(decorator_name, xeno.singleton(generic_wrapper))

    def _generic_task_queue_func_wrapper(self, f, decorator_name, queue_class):
        @functools.wraps(f)
        def queue_wrapper(mod_self, *args, **kwargs):
            task_list = f(mod_self, *args, **kwargs)

            if not isinstance(task_list, (list, tuple)):
                raise ValueError('%s decorated function "%s" should provide a list of Actionable objects.' % (
                    decorator_name, short_name_for_function(f)))
            if queue_class is ParallelTaskQueue:
                return queue_class(name_for_function(f), get_process_pool(), tasks = task_list)
            else:
                return queue_class(name_for_function(f), tasks = task_list)

        return _decorate(decorator_name, xeno.singleton(queue_wrapper))

    def input(self, f):
        """ Marks the given function as providing input to another resource. """
        return self._generic_task_func_wrapper(f, '@input')

    def output(self, f):
        """ Marks the given function as providing a cleanable output. """
        def wrapper(obj):
            if Cleanable.is_cleanable(obj):
                self.outputs.append(obj)

        return self._generic_task_func_wrapper(f, '@output', wrapper)

    def temporary(self, f):
        """ Marks the given function as providing a temporary result for another resource. """
        def wrapper(obj):
            if Cleanable.is_cleanable(obj):
                self.temp_outputs.append(obj)

        return self.target(self._generic_task_func_wrapper(f, '@temporary', wrapper))

    def parallel(self, f):
        """ Marks the given function as providing a list of actionables to be run in parallel. """
        return self._generic_task_queue_func_wrapper(f, '@parallel', ParallelTaskQueue)

    def queue(self, f):
        """ Marks the given function as providing a list of actionables to be run in sequence. """
        return self._generic_task_queue_func_wrapper(f, '@queue', TaskQueue)

    def setup(self, f):
        """ 
            Marks the given function as a setup function to be run before any other targets.
            Setup functions are not guaranteed to be run in any predictable order.
        """
        self.setup_resources.append(f.__name__)
        return xeno.provide(f)

    def default(self, f):
        """ Marks the given function as a build target, and subsequently the default target. """
        self.target(f)
        self.default_target = f.__name__
        return xeno.singleton(f)

    def target(self, f):
        """ Marks the given function as a build target. """
        self.targets.add(f.__name__)
        return xeno.singleton(_decorate('@target', f))

    def _aggregate_required_modules(self, modules):
        required_modules = []
        for module in modules:
            attrs = xeno.ClassAttributes.for_class(module)
            new_modules = attrs.get('bakery.required_modules', [])
            required_modules.extend(self._aggregate_required_modules(new_modules))
        return [*required_modules, *modules]

    def build(self, *modules):
        """
            Main method used to decorate a module as a build module.

            Example usage (via the default Build instance in a Bakefile)

            @build
            class MyBuild:
                @default
                def hello(self):
                    print('hello, world!')
        """
        results = []
        current_target = '<root>'
        Build.build_count += 1
        required_modules = [m() for m in self._aggregate_required_modules(modules)]
        injector = xeno.Injector(self, *required_modules)

        if not self.targets:
            raise BuildError('No targets defined in the build module.')

        targets = self.config.targets
        if not targets:
            if len(self.targets) == 1:
                targets = [*self.targets]
            elif self.default_target is not None:
                targets = [self.default_target]
            else:
                raise BuildError('No target was specified and no default target was provided.')

        try:
            evaluator = None
            if self.config.is_cleaning():
                evaluator = TaskEvaluator(CleanupTaskDecider(self.config))
            else:
                evaluator = TaskEvaluator(BuildTaskDecider())
            
            for target in targets:
                if not target in self.targets:
                    raise BuildError('Undefined target: "%s"' % target)

            for setup_resource in self.setup_resources:
                injector.require(setup_resource)

            results = evaluator.evaluate(injector, targets)
            BuildLog.get(self).success("BUILD SUCCEEDED")
        
        except Exception as e:
            BuildLog.get(self).error("BUILD FAILED (%s): %s" % (current_target, str(e)))
            if self.config.is_debug():
                raise e

        finally:
            # Clean up all temporary outputs
            if not self.config.clean:
                for temp_output in self.temp_outputs:
                    temp_output.clean()

        return results
    
    def __call__(self, class_):
        self.build(class_)
        return class_

#--------------------------------------------------------------------
def require(module_spec):
    """
        Decorator used to specify a class object or Python module
        path as a required build module.  If a Python module path is
        given, that module must export a class named 'Module' which
        is used as the required build module.

        This paradigm is used by the builtin Bakery recipes to
        provide facilities to Bakefiles that need to perform tasks
        related to C/C++ for example.

        Example (in a Bakefile):

        @build
        @require('bakery.recipe.cpp')
        class ExampleCppProgram:
            @temporary
            def object(self, builder):
                return builder.compile('main.cpp')

            @default
            def build(self, builder, object):
                return builder.link([object], 'program')
    """
    def wrapper(class_):
        attrs = xeno.ClassAttributes.for_class(class_, write = True)
        Module = None
        if inspect.isclass(module_spec):
            Module = module_spec
        else:
            module_import_path = module_spec.replace('/', '.')
            Module = __import__(module_import_path, globals(), locals(), ['Module']).Module
        dep_attrs = xeno.ClassAttributes.for_class(Module)
        if dep_attrs.get('namespace', None):
            class_ = xeno.using(dep_attrs.get('namespace'))(class_)
        required_modules = attrs.get('bakery.required_modules', [])
        required_modules.append(Module)
        attrs.put('bakery.required_modules', required_modules)
        return class_
    return wrapper

#--------------------------------------------------------------------
# Define the global default build object.
#
build = Build()
input = build.input
output = build.output
temporary = build.temporary
setup = build.setup
default = build.default
target = build.target
queue = build.queue
parallel = build.parallel
namespace = xeno.namespace
alias = xeno.alias
using = xeno.using

