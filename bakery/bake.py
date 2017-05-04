#--------------------------------------------------------------------
# bakery.bake: Bakery build command.  Runs a Bakefile.py file.
#
# Author: Lain Supe (supelee)
# Date: Friday, April 7th 2017
#--------------------------------------------------------------------

import os
import sys

#--------------------------------------------------------------------
BAKEFILE_NAME = 'Bakefile.py'

#--------------------------------------------------------------------
def main():
    if not os.path.exists(BAKEFILE_NAME):
        print('FATAL: No Bakefile.py in the current directory.')
        sys.exit(1)

    exec(open(BAKEFILE_NAME).read(), globals())

#--------------------------------------------------------------------
if __name__ == '__main__':
    main()
