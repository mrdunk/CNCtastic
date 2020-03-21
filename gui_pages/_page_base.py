from typing import Dict
from component import _ComponentBase
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase


class _GuiPageBase(_ComponentBase):
    """ Base class for layout of GUI tabs. """
    is_valid_plugin = False
    plugin_type = "gui_pages"

    def __init__(self,
                 interfaces: Dict[str, _InterfaceBase],
                 controllers: Dict[str, _ControllerBase]) -> None:
        super().__init__(self.label)
        self.interfaces: Dict[str, _InterfaceBase] = interfaces
        self.controllers: Dict[str, _ControllerBase] = controllers
