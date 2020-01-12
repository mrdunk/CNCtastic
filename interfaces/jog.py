from typing import Dict
from math import log10, floor
from collections import deque

import PySimpleGUI as sg

from interfaces._interfaceBase import _InterfaceBase
from definitions import FlagState

className = "JogWidget"

def round1SF(number) -> float:
    return round(number, -int(floor(log10(abs(number)))))

class JogWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    def __init__(self, label: str = "jogWidget"):
        self.label = label
        # Map incoming events to local member variables and callback methods.
        self.eventActions = {
                self.keyGen("xyMultiply"): ("_xyJogStepMultiply", 10),
                self.keyGen("xyDivide"): ("_xyJogStepMultiply", 0.1),
                self.keyGen("xyJogStep"): ("_xyJogStep", None),
                self.keyGen("zMultiply"): ("_zJogStepMultiply", 10),
                self.keyGen("zDivide"): ("_zJogStepMultiply", 0.1),
                self.keyGen("zJogStep"): ("_zJogStep", None),
                self.keyGen("ul"): ("_moveHandler", (-1, -1)),
                self.keyGen("uc"): ("_moveHandler", (0, -1)),
                self.keyGen("ur"): ("_moveHandler", (1, -1)),
                self.keyGen("cl"): ("_moveHandler", (-1, 0)),
                self.keyGen("cr"): ("_moveHandler", (1, 0)),
                self.keyGen("dl"): ("_moveHandler", (-1, 1)),
                self.keyGen("dc"): ("_moveHandler", (0, 1)),
                self.keyGen("dr"): ("_moveHandler", (1, 1)),
                }

        self.exported = {
                #self.keyGen("xyJogStep"): "_xyJogStep"
                }

        super().__init__(label)

        self._xyJogStep = 10
        self._zJogStep = 10

    def _xyJogStepMultiply(self, multiplier):
        self._xyJogStep = round1SF(self._xyJogStep * multiplier)
        # Need to explicitly push this here as the GUI also sends an update with
        # the old value. This publish will take effect later.
        self.publishOneByValue(self.keyGen("xyJogStep"), self._xyJogStep)

    def _zJogStepMultiply(self, multiplier):
        self._zJogStep = round1SF(self._zJogStep * multiplier)
        # Need to explicitly push this here as the GUI also sends an update with
        # the old value. This publish will take effect later.
        self.publishOneByValue(self.keyGen("zJogStep"), self._zJogStep)

    def _moveHandler(self, values):
        self.absoluteDistanceMode(self, False)
        self.moveTo(x=self._xyJogStep * values[0], y=self._xyJogStep * values[1])

    def guiLayout(self):
        def txt(label: str) -> sg.Frame:
            t = sg.Text(label, justification="center", size=(4, 2),
                    #background_color="grey"
                    )
            #return t
            return sg.Frame(title="", size=(4, 2), layout=[[t]], border_width=0)

        def but(label: str, key: str) -> sg.Button:
            return sg.Button(label, key=self.keyGen(key), size=(4, 2))

        def drp(key: str) -> sg.Drop:
            drop = sg.Drop(key=self.keyGen(key),
                       #enable_events=False,
                       values=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
                       default_value=self._xyJogStep, size=(5, 1))
            return sg.Frame(title="", size=(4, 2), layout=[[drop]], border_width=0, element_justification="left")
        
        layoutXY = [
                [txt(""),  txt(""),        txt("Y"),       txt("")],
                [txt(""),  but("", "ul"),  but("^", "uc"), but("", "ur")],
                [txt("X"), but("<", "cl"), but("0", "cc"), but(">", "cr")],
                [txt(""),  but("", "dl"),  but("v", "dc"), but("", "dr")],
                [txt(""),  but("/10","xyDivide"), drp("xyJogStep"), but("x10", "xyMultiply")],
                ]
        layoutZ = [
                [txt("Z")],
                [but("^", "uz")],
                [but("0", "cz")],
                [but("v", "dz")],
                [but("/10","zDivide"), drp("zJogStep"), but("x10", "zMultiply")],
                ]

        layout = [
                [sg.Column(layoutXY, element_justification="center", justification="left", pad=(0,0)),
                 sg.Column(layoutZ, element_justification="center", justification="left", pad=(0,0))]
                ]
        return layout

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
