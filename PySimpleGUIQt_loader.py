import sys
import os 
BASEDIR = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
sys.path.insert(0, os.path.join(BASEDIR, "PySimpleGUI/PySimpleGUIQt/"))

import PySimpleGUIQt as sg
if hasattr(sg, "__version__"):
    print("PySimpleGUIQt version: %s" % sg.__version__)
elif hasattr(sg, "version"):
    print("PySimpleGUIQt version: %s" % sg.version)

