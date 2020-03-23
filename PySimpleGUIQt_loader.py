# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
# pylint: disable=C0103 #  Module name "PySimpleGUIQt_loader" doesn't conform to snake_case naming style (invalid-name)

""" Load specific version of PySimpleGUI. """

import sys
import os
BASEDIR = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
sys.path.insert(0, os.path.join(BASEDIR, "PySimpleGUI/PySimpleGUIQt/"))

# pylint: disable=C0413 #  Import "import PySimpleGUIQt as sg" should be placed at the top of the module (wrong-import-position)
import PySimpleGUIQt as sg
if hasattr(sg, "__version__"):
    print("PySimpleGUIQt version: %s" % sg.__version__)
elif hasattr(sg, "version"):
    print("PySimpleGUIQt version: %s" % sg.version)
