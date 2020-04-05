from typing import List, Dict, Type, Optional
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

        self.filename_candidate: str = ""
        self.widgets: Dict[str, Any] = {}

        self.event_subscriptions[self.key_gen("file")] = ("filename_candidate", "")
        self.event_subscriptions[self.key_gen("cancel_gcode_file")] = ("on_file_cancel", "")
        self.event_subscriptions[self.key_gen("load_gcode_file")] = ("on_file_picked", "")

    def _file_picker(self) -> sg.Frame:
        self.widgets["file_picker"] = sg.Input(size=(30, 1), key=self.key_gen("file"))
        self.widgets["feedback"] = sg.Text(key=self.key_gen("feedback"))
        widget = sg.Frame("File picker",
                          [
                              [sg.Text('Filename')],
                              [self.widgets["file_picker"], sg.FileBrowse(size=(5, 1))],
                              [sg.OK(key=self.key_gen("load_gcode_file")),
                               sg.Cancel(key=self.key_gen("cancel_gcode_file"))],
                              [self.widgets["feedback"]],
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

    def on_file_picked(self, event_name: str, event_value: any) -> None:
        """ Called in response to gcode file being selected. """
        lines = []
        try:
            with open(self.filename_candidate) as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
        except IOError as e:
            self.widgets["feedback"].Update(value="Error: %s" % str(e))
            print(e)

        if lines:
            self.widgets["feedback"].Update(value="Loaded: %s" % self.filename_candidate)
            self.publish("component_gcode:raw_gcode_loaded", lines)
        else:
            self.widgets["feedback"].Update(value="File empty: %s" % self.filename_candidate)

    def on_file_cancel(self, event_name: str, event_value: any) -> None:
        """ Called in response to Cancel button. """

        print("on_file_cancel", event_name, event_value)
        self.filename_candidate = ""
        self.widgets["file_picker"].Update(value="")
        self.widgets["feedback"].Update(value="")
