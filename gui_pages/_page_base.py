""" Base class for top level GUI pages. Each page gets it's own tab. """

from typing import Dict, Type
from core.component import _ComponentBase
from controllers._controller_base import _ControllerBase


class _GuiPageBase(_ComponentBase):
    """ Base class for layout of GUI tabs. """
    is_valid_plugin = False
    plugin_type = "gui_pages"

    def __init__(self,
                 controllers: Dict[str, _ControllerBase],
                 controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        super().__init__(self.label)
        self.controllers: Dict[str, _ControllerBase] = controllers
        self.controller_classes: Dict[str, Type[_ControllerBase]] = controller_classes
