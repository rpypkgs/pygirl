#!/usr/bin/env python
import os, py, pdb, sys, time
from pygirl.profiling.gameboy_profiling_implementation import GameBoyProfiler

ROM_PATH = str(py.path.local(__file__).dirpath().dirpath().dirpath()) + "/lang/gameboy/rom"


def entry_point(argv=None):
    if argv is not None and len(argv) > 1:
        filename = argv[1]
        execution_seconds = float(argv[2])
    else:
        pos = str(9)
        filename = ROM_PATH + "/rom" + pos + "/rom" + pos + ".gb"
        execution_seconds = 600
    gameBoy = GameBoyProfiler()
    try:
        gameBoy.load_cartridge_file(str(filename))
    except:
        gameBoy.load_cartridge_file(str(filename), verify=False)

    start = time.time()
    gameBoy.mainLoop(execution_seconds)
    print time.time() - start

    return 0


# _____ Define and setup target ___

def target(*args):
    return entry_point, None


def test_target():
    entry_point(sys.argv)


# STARTPOINT ===================================================================

if __name__ == '__main__':
    test_target()
