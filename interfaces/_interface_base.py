""" Plugin providing interface to control of some aspect of the active controller. """

from typing import Union

from pygcode import block, GCodeCoordSystemOffset

from component import _ComponentBase


class _InterfaceBase(_ComponentBase):
    """ A base class for user input objects used for controlling the machine. """

    # Type of component. Used by the plugin loader.
    plugin_type = "interface"
