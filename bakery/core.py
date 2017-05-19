#--------------------------------------------------------------------
# bakery.cxx: Modules and Classes for building C++ artifacts.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import argparse
import functools
import logging
import os
import sys
import xeno

from .util import *
from .file import *
from .work import *

#--------------------------------------------------------------------
class BuildError(Exception):
    pass

#--------------------------------------------------------------------
class Config:
    def __init__(self):
        self.debug = False
        self.target = None
        self.cleaning = False

    def get_arg_parser(self):
        parser = argparse.ArgumentParser(description = 'Execute targets in bakefiles.')
        parser.add_argument('target', metavar='TARGET', nargs='?', default=None)
        parser.add_argument('-D', '--debug', action='store_true')
        parser.add_argument('-c', '--clean', action='store_true')
        return parser

    def is_debug(self):
        return int(os.environ.get('BAKERY_DEBUG', "0")) or self.debug

    def parse_args(self):
        self.get_arg_parser().parse_args(namespace = self)
        return self

#--------------------------------------------------------------------
class Build:
    def __init__(self):
        self.outputs = []
        self.targets = set()
        self.temp_outputs = []
        self.setup_targets = []
        self.default_target = None

    @xeno.provide
    def build(self):
        return self
    
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
    
    def _digest_resource(self, attrs, name, resource, cleaning):
        if attrs.check('no_digest'):
            return resource

        def digest_impl(sub_resource):
            if not cleaning and isinstance(sub_resource, Task):
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
    
    def _get_injection_interceptor(self, cleaning = False):
        def intercept_injection(attrs, dependency_map):
            result = {}
            return {name: self._digest_resource(attrs, name, resource, cleaning) \
                    for (name, resource) in dependency_map.items()}
        return intercept_injection

    def __call__(self, *modules, target = None, exit = True, cleaning = False):
        injector = xeno.Injector(self, *modules)
        injector.add_injection_interceptor(self._get_injection_interceptor(cleaning))
        
        if not self.targets:
            raise BuildError('No targets defined in the build module.')

        if target is None:
            if len(self.targets) == 1:
                target = list(self.targets)[0]
            elif self.default_target is not None:
                target = self.default_target
            else:
                raise BuildError('No target was specified and no default target was provided.')

        log_for(self).info("Building target: %s" % target)
        
        try:
            # Run all of the setup targets first.
            for setup_target in self.setup_targets:
                injector.require(setup_target)
            
            if not target in self.targets:
                raise BuildError('Invalid or undefined target: "%s"' % target)
            
            # Build the specified target
            result_obj = injector.require(target)
            
            if cleaning:
                def cleanup_tasks(result):
                    if isinstance(result, Cleanable):
                        return wide_map(result.cleanup(), cleanup_tasks)

                def breakdown_tasks(result):
                    if isinstance(result, Breakable):
                        return wide_map(result.breakdown(), breakdown_tasks)
                
                result_obj = wide_map(result_obj, breakdown_tasks)
                wide_map(result_obj, cleanup_tasks)
                wide_map(self.outputs, cleanup_tasks)

            else:
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
namespace = xeno.namespace
alias = xeno.alias
using = xeno.using

