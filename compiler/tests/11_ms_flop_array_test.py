#!/usr/bin/env python2.7
"""
Run a regresion test on a dff_array.
"""

import unittest
from testutils import header
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
import debug
import calibre
import importlib

OPTS = globals.get_opts()

#@unittest.skip("SKIPPING 20_sram_test")


class dff_array_test(unittest.TestCase):

    def runTest(self):
        globals.init_openram("config_20_{0}".format(OPTS.tech_name))

        import ms_flop_array

        debug.info(2, "Testing ms_flop_array for columns=8, word_size=8")
        OPTS.check_lvsdrc = False
        a = ms_flop_array.ms_flop_array(columns=8, word_size=8)
        OPTS.check_lvsdrc = True
        self.local_check(a)

        # reset the static duplicate name checker for unit tests
        import design
        design.design.name_map=[]

        debug.info(2, "Testing ms_flop_array for columns=16, word_size=8")
        OPTS.check_lvsdrc = False
        a = ms_flop_array.ms_flop_array(columns=16, word_size=8)
        OPTS.check_lvsdrc = True
        self.local_check(a)
        
        globals.end_openram()

    def local_check(self, a):
        tempspice = OPTS.openram_temp + "temp.sp"
        tempgds = OPTS.openram_temp + "temp.gds"

        a.sp_write(tempspice)
        a.gds_write(tempgds)

        self.assertFalse(calibre.run_drc(a.name, tempgds))
        self.assertFalse(calibre.run_lvs(a.name, tempgds, tempspice))

        os.remove(tempspice)
        os.remove(tempgds)


# instantiate a copdsay of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
