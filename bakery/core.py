#--------------------------------------------------------------------
# bakery.cxx: Modules and Classes for building C++ artifacts.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import functools
import logging
import os
import sys
import xeno

from .util import *
from .file import *
from .work import *

#--------------------------------------------------------------------
def is_debug():
    return int(os.environ.get('BAKERY_DEBUG', "0"))

#--------------------------------------------------------------------
class BuildError(Exception):
    pass

#--------------------------------------------------------------------
class Build:
    def __init__(self):
        self.outputs = []
        self.targets = set()
        self.temp_outputs = []
        self.setup_targets = ['_build_init']
        self.default_target = None
        self.cleaning = False

    @xeno.provide
    def build(self):
        return self
    
    @xeno.provide
    def build_log_format(self):
        return '%(message)s'

    @xeno.provide
    def _build_init(self, build_log_format):
        # Setup stdout logging
        root = logging.getLogger()
        root.setLevel(logging.DEBUG if is_debug() else logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if is_debug() else logging.INFO)
        formatter = logging.Formatter(build_log_format)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def _generic_task_func_wrapper(self, f, decorator_name,
                                   task_callback = lambda x: None):
        def dispatch_result(result):
            if isinstance(result, Task):
                task_callback(result)
            return result
        
        @functools.wraps(f)
        def generic_wrapper(mod_self, *args, **kwargs):
            obj = f(mod_self, *args, **kwargs)
            return wide_map(obj, dispatch_result)

        return xeno.singleton(generic_wrapper)

    def input(self, f):
        return self._generic_task_func_wrapper(f, '@input')

    def output(self, f):
        def wrapper(obj):
            if isinstance(obj, Cleanable):
                self.outputs.append(obj)

        return self._generic_task_func_wrapper(f, '@output', wrapper)

    def temporary(self, f):
        def wrapper(obj):
            if isinstance(obj, Cleanable):
                self.temp_outputs.append(obj)

        return self._generic_task_func_wrapper(f, '@temporary', wrapper)

    def parallel(self, f):
        @functools.wraps(f)
        def parallel_wrapper(mod_self, *args, **kwargs):
            task_list = f(mod_self, *args, **kwargs)

            if not isinstance(task_list, (list, tuple)):
                raise ValueError('@parallel decorated function "%s" should provide a list of Task objects.' % (name_for_function(f)))
            return ParallelTaskQueue(name_for_function(f), tasks = task_list)

        return xeno.singleton(parallel_wrapper)
    
    def setup(self, f):
        self.setup_targets.append(f.__name__)
        return xeno.provide(f)

    def default(self, f):
        self.target(f)
        self.default_target = f.__name__
        return xeno.singleton(f)

    def target(self, f):
        self.targets.add(f.__name__)
        return xeno.singleton(f)
    
    def _clean_all_targets(self, injector):
        for target in self.targets:
            injector.require(target)

        outputs = [x for x in self.outputs if x.exists()]
        if outputs:
            log_for(self).info("Cleaning up output tasks...")
            for task in outputs:
                task.remove()
    
    def _digest_resource(self, attrs, name, resource):
        if attrs.check('no_digest'):
            return resource

        def digest_impl(sub_resource):
            if not self.cleaning and isinstance(sub_resource, Task):
                try:
                    return wide_map(sub_resource.run(), digest_impl)
                except Exception as e:
                    raise BuildError('Failed to build "%s", needed by "%s".' % (name, attrs.get('name'))) from e
            elif isinstance(sub_resource, Breakable):
                try:
                    return wide_map(sub_resource.breakdown(), digest_impl)

                except Exception as e:
                    raise BuildError('Failed to breakdown task "%s" while cleaning.' % name) from e
            else:
                return sub_resource
        
        return wide_map(resource, digest_impl)

    def _intercept_injection(self, attrs, dependency_map):
        result = {}
        return {name: self._digest_resource(attrs, name, resource) \
                for (name, resource) in dependency_map.items()}

    def __call__(self, *modules, target = None, exit = True):
        injector = xeno.Injector(self, *modules)
        injector.add_injection_interceptor(self._intercept_injection)
        
        if not self.targets:
            raise BuildError('No targets defined in the build module.')

        elif target is None and len(sys.argv) > 1:
            target = sys.argv[1]

        if target is None:
            if len(self.targets) == 1:
                target = list(self.targets)[0]
            elif self.default_target is not None:
                target = self.default_target
            else:
                raise BuildError('No target was specified and no default target was provided.')

        if target == 'clean':
            self.cleaning = True

        log_for(self).info("Building target: %s" % target)
        
        try:
            # Run all of the setup targets first.
            for setup_target in self.setup_targets:
                injector.require(setup_target)
            
            # If we are trying to clean, we should do that instead.
            if self.cleaning:
                return self._clean_all_targets(injector)

            elif not target in self.targets:
                raise BuildError('Invalid or undefined target: "%s"' % target)
            
            # Build the specified target
            result_obj = injector.require(target)

            def evaluate_tasks(result):
                if isinstance(result, Task):
                    return wide_map(result.run(), evaluate_tasks)

            result_obj = wide_map(result_obj, evaluate_tasks)
            
            log_for(self).info("BUILD SUCCEEDED")
            if exit:
                sys.exit(0)
            else:
                return result_obj
        
        except Exception as e:
            log_for(self).error("BUILD FAILED: %s" % str(e), exc_info=is_debug())

            if exit and not is_debug():
                sys.exit(1)
            else:
                raise e

        finally:
            # Clean up all temporary outputs
            for temp_output in self.temp_outputs:
                temp_output.cleanup()

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
parallel = build.parallel

