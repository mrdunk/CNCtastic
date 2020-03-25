# Pylint seems to be looking at python2.7's PySimpleGUI libraries so we need the following:
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" Interface to allow text entry of raw Gcode. """

from typing import List, Deque, Optional
from collections import deque

from pygcode import Line
from pygcode.exceptions import GCodeWordStrError

from PySimpleGUIQt_loader import sg

from interfaces._interface_base import _InterfaceBase

class Terminal(_InterfaceBase):
    """ Allows user to enter raw Gcode as text. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    def __init__(self, label: str = "terminal") -> None:
        super().__init__(label)

        # Map incoming events to local member variables and callback methods.
        self.event_subscriptions = {
            self.key_gen("gcode_newline"): ("_gcode_update", None),
            self.key_gen("gcode_submit"): ("_gcode_submit", None),
            "user_feedback:command_state": ("_user_feedback", None)
        }

        self.widget_log: Optional[sg.Multiline] = None
        self.widget_newline: Optional[sg.Input] = None
        self.newline: str = ""
        # TODO Workaround for https://github.com/PySimpleGUI/PySimpleGUI/issues/2623
        # Remove this when the `autoscroll` parameter works.
        self.log: Deque[str] = deque()

    def _user_feedback(self, value: str) -> None:
        self.log.append(str((value, False)))
        self._update_content()

    def _gcode_update(self, gcode: str) -> None:
        self.newline = gcode

    def _gcode_submit(self, key: str, value: str) -> None:
        if not self.widget_newline:
            return

        self.widget_newline.Update(value="")

        # TODO The rest of this method is a workaround for
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/2623
        # When the `autoscroll` parameter works we will be able to use:
        # self.widget_log.Update(value=newline, append=True)

        valid = self._raw_gcode(self.newline)
        newline = "> %s\n" % (str(self.newline) if valid else self.newline)

        self.log.append(str((newline, valid)))
        self.newline = ""

        self._update_content()

    def _update_content(self) -> None:
        """ Redraw the terminal window contents. """
        if not self.widget_log:
            return

        while len(self.log) > self.widget_log.metadata["size"][1]:
            self.log.popleft()
        self.widget_log.Update(value="")
        for line in self.log:
            text_color = "blue" if line[1] else "red"
            self.widget_log.Update(
                value=line[0], append=True, text_color_for_value=text_color)

    def gui_layout(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        log_size = (60, 10)
        self.widget_log = sg.Multiline(
            key=self.key_gen("log"),
            size=log_size,
            disabled=True,
            autoscroll=True,
            metadata={"skip_update": True, "size": log_size},
            )

        self.widget_newline = sg.Input(
            size=(60, 1),
            key=self.key_gen("gcode_newline"),
            metadata={"skip_update": True},
            focus=True,
            )

        layout = [
            [sg.Text("Title:", size=(20, 1))],
            [self.widget_log],
            [self.widget_newline],
            [sg.Button(
                "Submit",
                visible=False,
                key=self.key_gen("gcode_submit"),
                bind_return_key=True,
                )],
            ]
        return layout

    def _raw_gcode(self, raw_gcode: str) -> bool:
        try:
            line = Line(str(raw_gcode).strip())
        except GCodeWordStrError:
            return False
        self.publish("command:gcode", line.block)
        print(line.block)
        return True
