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

        # Map events to local member variables and callback methods.
        self.eventActions = {
                self.keyGen("multiply"): ("_xyJogStepMultiply", 10),
                self.keyGen("divide"): ("_xyJogStepMultiply", 0.1),
                self.keyGen("xyJogStep"): ("_xyJogStep", None),
                self.keyGen("ul"): ("_moveHandler", (-1, -1)),
                self.keyGen("uc"): ("_moveHandler", (0, -1)),
                self.keyGen("ur"): ("_moveHandler", (1, -1)),
                self.keyGen("cl"): ("_moveHandler", (-1, 0)),
                self.keyGen("cr"): ("_moveHandler", (1, 0)),
                self.keyGen("dl"): ("_moveHandler", (-1, 1)),
                self.keyGen("dc"): ("_moveHandler", (0, 1)),
                self.keyGen("dr"): ("_moveHandler", (1, 1)),
                }

        self._xyJogStep = 10

    def _xyJogStepMultiply(self, multiplier):
        self._xyJogStep = round1SF(self._xyJogStep * multiplier)

    def _moveHandler(self, values):
        self.absoluteDistanceMode(self, False)
        self.moveTo(x=self._xyJogStep * values[0], y=self._xyJogStep * values[1])

    def exportToGui(self) -> Dict:
        """ Export values to be consumed by GUI.
        Returns:
            A Dict where the key is the key of the GUI widget to be populated
            and the value is a member od this class. """
        return {
                self.keyGen("xyJogStep"): self._xyJogStep,
                }

    def guiLayout(self):
        layout = [
                [sg.Button("", key=self.keyGen("ul"), size=(4, 2), pad=(0, 0)),
                 sg.Button("^", key=self.keyGen("uc"), size=(4, 2), pad=(0, 0)),
                 sg.Button("", key=self.keyGen("ur"), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Button("x10", key=self.keyGen("multiply"), size=(2, 1), pad=(0, 0)),
                 #sg.Button("+", key=self.keyGen("add"), size=(2, 1), pad=(0, 0))
                 ],
                [sg.Button("<", key=self.keyGen("cl"), size=(4, 2), pad=(0, 0)),
                 sg.Button("0", key=self.keyGen("cc"), size=(4, 2), pad=(0, 0)),
                 sg.Button(">", key=self.keyGen("cr"), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Drop(key=self.keyGen("xyJogStep"),
                     values=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
                     default_value=self._xyJogStep, size=(6, 1)),
                 ],
                [sg.Button("", key=self.keyGen("dl"), size=(4, 2), pad=(0, 0)),
                 sg.Button("v", key=self.keyGen("dc"), size=(4, 2), pad=(0, 0)),
                 sg.Button("", key=self.keyGen("dr"), size=(4, 2), pad=(0, 0)),
                 sg.Text(" "),
                 sg.Button("/10", key=self.keyGen("divide"), size=(2, 1), pad=(0, 0)),
                 #sg.Button("-", key=self.keyGen("minus"), size=(2, 1), pad=(0, 0))
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
