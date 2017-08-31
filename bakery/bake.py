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
PREAMBLE = """
from bakery import *
from bakery.core import Build
Build.global_config.parse_args()
"""

#--------------------------------------------------------------------
def main():
    """
        The main entry point of the 'bake' command line tool.
        Prepends the PREAMBLE source to the contents of 'Bakefile.py'
        in the current directory, or the file specified by the '-b'
        command line switch, and executes the resulting script.
    """
    bakefile_name = BAKEFILE_NAME
    if '-b' in sys.argv and len(sys.argv) > sys.argv.index('-b'):
        bakefile_name = sys.argv[sys.argv.index('-b') + 1]

    if not os.path.exists(bakefile_name):
        print('FATAL: No %s in the current directory.' % bakefile_name)
        sys.exit(1)

    bake_instructions = PREAMBLE + open(bakefile_name).read()

    exec(bake_instructions, globals())

    if Build.build_count == 0:
        BuildLog.get(main, log = False).warning('Nothing was built, did you forget to call build() with modules?')

#--------------------------------------------------------------------
if __name__ == '__main__':
    main()
