from typing import Dict
from math import log10, floor
from collections import deque

#import PySimpleGUIQt as sg
from terminals.gui import sg

from interfaces._interfaceBase import _InterfaceBase
from definitions import FlagState

className = "JogWidget"

def round1SF(number) -> float:
    return round(number, -int(floor(log10(abs(number)))))

class JogWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    def __init__(self, label: str = "jogWidget"):
        super().__init__(label)

        self.label = label
        # Map incoming events to local member variables and callback methods.
        self.eventSubscriptions = {
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
        butW = 5
        butH = 1.5
        def txt(label: str) -> sg.Frame:
            t = sg.Text(label, justification="center", size=(butW, butH),
                    #background_color="grey"
                    )
            return t

        def but(label: str, key: str) -> sg.Button:
            return sg.Button(label, key=self.keyGen(key), size=(butW, butH))

        def drp(key: str) -> sg.Drop:
            drop = sg.Drop(key=self.keyGen(key),
                       #enable_events=False,
                       values=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
                       default_value=self._xyJogStep, size=(butW, 1))
            return drop
        
        layoutXY = [
                [txt(""),  txt(""),        txt("Y"),       txt("")],
                [txt(""),  but("", "ul"),  but("^", "uc"), but("", "ur")],
                [txt("X"), but("<", "cl"), but("0", "cc"), but(">", "cr")],
                [txt(""),  but("", "dl"),  but("v", "dc"), but("", "dr")],
                [txt("")],
                [txt(""),  but("/10","xyDivide"), drp("xyJogStep"), but("x10", "xyMultiply")],
                ]
        layoutZ = [
                [txt(""), txt("Z")],
                [txt(""), but("^", "uz")],
                [txt(""), but("0", "cz")],
                [txt(""), but("v", "dz")],
                [txt("")],
                [but("/10","zDivide"), drp("zJogStep"), but("x10", "zMultiply")],
                ]

        layout = [
                [sg.Column(layoutXY, pad=(0,0), size=(1,1)),
                 sg.Column(layoutZ, pad=(0,0), size=(1,1)),
                 #sg.Stretch()
                 ]
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
