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

from xeno import Injector, provide

from .util import *
from .file import *

#--------------------------------------------------------------------
def is_debug():
    return int(os.environ.get('BAKERY_DEBUG', "0"))

#--------------------------------------------------------------------
class BuildError(Exception):
    pass

#--------------------------------------------------------------------
class Build:
    def __init__(self):
        self.log = logger_for_class(self)
        self.outputs = []
        self.targets = set()
        self.temp_outputs = []
        self.setup_targets = ['_build_init']
        self.default_target = None
        self.cleaning = False

    @provide
    def build(self):
        return self
    
    @provide
    def build_log_format(self):
        return '%(message)s'

    @provide
    def _build_init(self, build_log_format):
        # Setup stdout logging
        root = logging.getLogger()
        root.setLevel(logging.DEBUG if is_debug() else logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if is_debug() else logging.INFO)
        formatter = logging.Formatter(build_log_format)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def provide(self, f):
        return provide(f)
    
    def _generic_file_func_wrapper(self, f, err_msg_prefix,
                                   callback = lambda x: None):
        @functools.wraps(f)
        def generic_wrapper(mod_self, *args, **kwargs):
            obj = f(mod_self, *args, **kwargs)
            obj_list = list(flat_map([obj]))
            for item in obj_list:
                if not isinstance(item, File):
                    raise ValueError('%s decorated provider "%s" should provide a File object or list of File objects.' % (err_msg_prefix, f.__name__))
            for file in obj_list:
                callback(file)

            return obj

        return provide(generic_wrapper)

    def input(self, f):
        return self._generic_file_func_wrapper(f, '@input')

    def output(self, f):
        def wrapper(file):
            self.outputs.append(file)

        return self._generic_file_func_wrapper(f, '@output', wrapper)

    def temporary(self, f):
        def wrapper(file):
            self.temp_outputs.append(file)
        
        return self._generic_file_func_wrapper(f, '@temporary', wrapper)

    def setup(self, f):
        self.setup_targets.append(f.__name__)
        return provide(f)

    def default(self, f):
        self.target(f)
        self.default_target = f.__name__
        return f

    def target(self, f):
        self.targets.add(f.__name__)
        return f
    
    def _clean_all_targets(self, injector):
        for target in self.targets:
            injector.require(target)

        outputs = [x for x in self.outputs if x.exists()]
        if outputs:
            self.log.info("Cleaning up output files...")
            for file in outputs:
                file.remove()

    def __call__(self, *modules, target = None, exit = True):
        injector = Injector(self, *modules)
        
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

        self.log.info("Building target: %s" % target)
        
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

            # If the result contains files, build them and then verify that they actually exist.
            result_list = list(flat_map([result_obj]))
            for result in result_list:
                if isinstance(result, File):
                    result.build()
                    if not result.exists():
                        raise BuildError('Target file build succeeded but file does not exist: %s' % result.relpath())
            
            self.log.info("BUILD SUCCEEDED")
            if exit:
                sys.exit(0)
            else:
                return result_obj
        
        except Exception as e:
            self.log.error("BUILD FAILED: %s" % str(e), exc_info=is_debug())

            if exit:
                sys.exit(1)
            else:
                raise e

        finally:
            # Clean up all temporary files.
            temp_outputs = [x for x in self.temp_outputs if x.exists()]
            if temp_outputs:
                self.log.info("Cleaning up temporary files...")
                for temp_file in self.temp_outputs:
                    temp_file.remove()

#--------------------------------------------------------------------
# Define the global default build object.
build = Build()

#--------------------------------------------------------------------
def input(f):
    return build.input(f)

#--------------------------------------------------------------------
def output(f):
    return build.output(f)

#--------------------------------------------------------------------
def temporary(f):
    return build.temporary(f)

#--------------------------------------------------------------------
def setup(f):
    return build.setup(f)

#--------------------------------------------------------------------
def default(f):
    return build.default(f)

#--------------------------------------------------------------------
def target(f):
    return build.target(f)

#--------------------------------------------------------------------
def no_rebuild(f):
    @functools.wraps(f)
    def wrap_build(self, *args, **kwargs):
        if not self.exists():
            return f(self, *args, **kwargs)
    return wrap_build

