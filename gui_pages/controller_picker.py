from typing import List
from gui_pages._page_base import _GuiPageBase
from terminals.gui import sg

class ControllerPicker(_GuiPageBase):
    is_valid_plugin = True

    label = "ControllerPicker"

    def gui_layout(self) -> List[List[List[sg.Element]]]:
        output = [
                [sg.Button("Restart", size=(8, 2), key="gui:restart")],
            ]

        return output

