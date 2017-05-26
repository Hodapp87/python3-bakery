#--------------------------------------------------------------------
# bakery.bake: Bakery build command.  Runs a Bakefile.py file.
#
# Author: Lain Supe (supelee)
# Date: Friday, April 7th 2017
#--------------------------------------------------------------------

import os
import sys

from .log import BuildLog

#--------------------------------------------------------------------
BAKEFILE_NAME = 'Bakefile.py'
PRELUDE = """
from bakery import *
from bakery.core import Build
Build.global_config.parse_args()
"""

#--------------------------------------------------------------------
def is_debug():
    return os.environ.get('BAKERY_DEBUG') == '1'

#--------------------------------------------------------------------
def debug_print_instruction_lines(instructions):
    lines = instructions.split('\n')
    for n in range(len(lines)):
        print("%d: %s" % (n, lines[n]))

#--------------------------------------------------------------------
def main():
    if not os.path.exists(BAKEFILE_NAME):
        print('FATAL: No %s in the current directory.' % BAKEFILE_NAME)
        sys.exit(1)

    bake_instructions = PRELUDE + open(BAKEFILE_NAME).read()
    if is_debug():
        debug_print_instruction_lines(bake_instructions)

    exec(bake_instructions, globals())

    if Build.build_count == 0:
        BuildLog.get(main, log = False).warning('Nothing was built, did you forget to call build() with modules?')

#--------------------------------------------------------------------
if __name__ == '__main__':
    main()
