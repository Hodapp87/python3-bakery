#--------------------------------------------------------------------
# bakery.core: Core modules and features of the Bakery build system.
#
# Author: Lain Supe (supelee)
# Date: Thursday, March 23 2017
#--------------------------------------------------------------------

import argparse
import inspect
import functools
import logging
import os
import sys
import xeno

from .util import *
from .file import *
from .work import *
from .log import *

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
    build_count = 0

    def __init__(self):
        self.outputs = []
        self.targets = set()
        self.temp_outputs = []
        self.setup_targets = []
        self.default_target = None
        self.config = Config()
        self.modules = []

    @xeno.provide
    @xeno.named('build')
    def get_build(self):
        return self

    @xeno.provide
    @xeno.named('~config')
    def config(self):
        return self.config

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

    def _digest_resource(self, attrs, name, resource):
        if attrs.check('no_digest'):
            return resource

        def digest_impl(sub_resource):
            if not self.config.cleaning and isinstance(sub_resource, Task):
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

    def _get_injection_interceptor(self):
        def intercept_injection(attrs, dependency_map):
            result = {}
            return {name: self._digest_resource(attrs, name, resource) \
                    for (name, resource) in dependency_map.items()}
        return intercept_injection

    def _aggregate_required_modules(self, modules):
        required_modules = []
        for module in modules:
            attrs = xeno.ClassAttributes.for_class(module)
            required_modules.extend(attrs.get('bakery::required_modules', []))
        return [*required_modules, *modules]

    def __call__(self, *modules, target = None, exit = True):
        def wrapper(clazz):
            Build.build_count += 1
            required_modules = [m() for m in self._aggregate_required_modules([*modules, clazz])]

            injector = xeno.Injector(self, *required_modules)
            injector.add_injection_interceptor(self._get_injection_interceptor())

            if not self.targets:
                raise BuildError('No targets defined in the build module.')

            build_target = target
            if build_target is None:
                if len(self.targets) == 1:
                    build_target = list(self.targets)[0]
                elif self.default_target is not None:
                    build_target = self.default_target
                else:
                    raise BuildError('No target was specified and no default target was provided.')

            BuildLog.get(self).target("Building target: %s" % build_target)

            try:
                # Run all of the setup targets first.
                for setup_target in self.setup_targets:
                    injector.require(setup_target)

                if not build_target in self.targets:
                    raise BuildError('Invalid or undefined target: "%s"' % build_target)

                # Build the specified target
                result_obj = injector.require(build_target)

                if self.config.cleaning:
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

                    BuildLog.get(self).success("BUILD SUCCEEDED")
                    if exit:
                        sys.exit(0)
                    else:
                        return result_obj

            except Exception as e:
                BuildLog.get(self).error("BUILD FAILED: %s" % str(e), exc_info=is_debug())

                if exit and not is_debug():
                    sys.exit(1)
                else:
                    raise e

            finally:
                # Clean up all temporary outputs
                for temp_output in self.temp_outputs:
                    temp_output.cleanup()

            return clazz
        return wrapper

#--------------------------------------------------------------------
def require(module_name):
    def wrapper(clazz):
        attrs = xeno.ClassAttributes.for_class(clazz, write = True)
        Module = __import__(module_name, globals(), locals(), ['Module']).Module
        dep_attrs = xeno.ClassAttributes.for_class(Module)
        if dep_attrs.get('namespace', None):
            clazz = xeno.using(dep_attrs.get('namespace'))(clazz)
        required_modules = attrs.get('bakery::required_modules', [])
        required_modules.append(Module)
        attrs.put('bakery::required_modules', required_modules)
        return clazz
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
parallel = build.parallel
namespace = xeno.namespace
alias = xeno.alias
using = xeno.using

