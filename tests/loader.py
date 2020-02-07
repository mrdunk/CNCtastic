""" Add code to be tested to the path so includes can find it. """

import sys
import os

TESTDIR = os.path.dirname(__file__)
SRCDIR = '../'
sys.path.insert(0, os.path.abspath(os.path.join(TESTDIR, SRCDIR)))
