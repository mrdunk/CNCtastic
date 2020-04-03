from typing import List, Dict, Type
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase
from gui_pages._page_base import _GuiPageBase

# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
from PySimpleGUIQt_loader import sg

class GcodeLoader(_GuiPageBase):
    """ A GUI page for selecting and configuring controllers. """
    is_valid_plugin = True

    label = "GcodeLoader"

    def __init__(self,
                 interfaces: Dict[str, _InterfaceBase],
                 controllers: Dict[str, _ControllerBase],
                 controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        super().__init__(interfaces, controllers, controller_classes)
   
    def _file_picker(self) -> sg.Frame:
        widget = sg.Frame("File picker",
                          [
                              [sg.Text('Filename')],
                              [sg.Input(size=(30, 1)), sg.FileBrowse(size=(5, 1))],
                              [sg.OK(), sg.Cancel()]
                          ],
                          size=(30, 30),
                          #visible=visible,
                          )
        return widget

    def gui_layout(self) -> List[List[List[sg.Element]]]:
        """ Return the GUI page for uploading Gcode. """
        output = [
            [self._file_picker()]
            ]
        return output
