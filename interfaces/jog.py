from typing import Dict
from math import log10, floor

import PySimpleGUI as sg

from interfaces._guiInterfaceBase import _GuiInterfaceBase
from interfaces._interfaceBase import UpdateState, InterfaceState
from definitions import FlagState, State

className = "JogWidget"

def round1SF(number) -> float:
    return round(number, -int(floor(log10(abs(number)))))

class JogWidget(_GuiInterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    def __init__(self, label: str = "jogWidget"):
        super().__init__(label)
        self.readyForPush = True
        self.readyForPull = False

        self.eventActions = {
                ("%s:multiply" % label): ("_xyJogStepMultiply", 10),
                ("%s:divide" % label): ("_xyJogStepMultiply", 0.1),
                ("%s:xyJogStep" % label): ("_xyJogStep", None),
                ("%s:ul" % label): ("_moveHandler", (-1, -1)),
                ("%s:uc" % label): ("_moveHandler", (0, -1)),
                ("%s:ur" % label): ("_moveHandler", (1, -1)),
                ("%s:cl" % label): ("_moveHandler", (-1, 0)),
                ("%s:cr" % label): ("_moveHandler", (1, 0)),
                ("%s:dl" % label): ("_moveHandler", (-1, 1)),
                ("%s:dc" % label): ("_moveHandler", (0, 1)),
                ("%s:dr" % label): ("_moveHandler", (1, 1)),
                }

        self._xyJogStep = 10

    def _xyJogStepMultiply(self, multiplier):
        self._xyJogStep = round1SF(self._xyJogStep * multiplier)

    def _moveHandler(self, values):
        self.absoluteDistanceMode(self, False)
        self.moveTo(x=self._xyJogStep * values[0], y=self._xyJogStep * values[1])

    def exportToGui(self) -> Dict:
        """ Export values in this class to be consumed by GUI.
        Returns:
            A Dict where the key is the key of the GUI widget to be populated
            and the value is a member od this class. """
        return {
                "%s:xyJogStep" % self.label: self._xyJogStep,
                }

    def guiLayout(self):
        layout = [
                [sg.Button("", key=("%s:ul" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button("^", key=("%s:uc" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button("", key=("%s:ur" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Button("x10", key=("%s:multiply" % self.label), size=(2, 1), pad=(0, 0)),
                 #sg.Button("+", key=("%s:add" % self.label, 10), size=(2, 1), pad=(0, 0))
                 ],
                [sg.Button("<", key=("%s:cl" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button("0", key=("%s:cc" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button(">", key=("%s:cr" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Drop(key="%s:xyJogStep" % self.label,
                     values=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
                     default_value=self._xyJogStep, size=(6, 1)),
                 ],
                [sg.Button("", key=("%s:dl" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button("v", key=("%s:dc" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Button("", key=("%s:dr" % self.label), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Button("/10", key=("%s:divide" % self.label), size=(2, 1), pad=(0, 0)),
                 #sg.Button("-", key=("%s:minus" % self.label, 10), size=(2, 1), pad=(0, 0))
                ],
                ]
        return layout

    def connect(self):
        self.status = InterfaceState.STALE_DATA
        return self.status

    def disconnect(self):
        self.status = InterfaceState.UNKNOWN
        return self.status

    def moveTo(self, **argkv):
        """ Move the machine head.
        Args:
            argkv: A dict containing one or more of the following parameters:
                command: The gcode command as a string. Defaults to "G01".
                x: The x coordinate.
                y: The y coordinate.
                z: The z coordinate.
                f: The feed rate.
        """
        super().moveTo(**argkv)
        self._updatedData.jog = FlagState.TRUE
