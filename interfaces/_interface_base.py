""" Plugin providing interface to control of some aspect of the active controller. """

from typing import List
from PySimpleGUIQt_loader import sg
from component import _ComponentBase

class _InterfaceBase(_ComponentBase):
    """ A base class for user input objects used for controlling the machine. """

    # Type of component. Used by the plugin loader.
    plugin_type = "interface"

    def gui_layout(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        assert False, "gui_layout() not implemented."
        return []

