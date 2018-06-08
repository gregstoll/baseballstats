#!/usr/bin/python3
import pstats
import sys

def printProfileData(fileName):
    p = pstats.Stats(fileName)
    p.strip_dirs().sort_stats('cumulative').print_stats(15)
    p.strip_dirs().sort_stats('time').print_stats(15)

if (__name__ == '__main__'):
    printProfileData(sys.argv[1])
