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

    def __init__(self, label: str = "jogWidget") -> None:
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
                self.keyGen("ul"): ("_moveHandler", (-1, 1, 0)),
                self.keyGen("uc"): ("_moveHandler", (0, 1, 0)),
                self.keyGen("ur"): ("_moveHandler", (1, 1, 0)),
                self.keyGen("cl"): ("_moveHandler", (-1, 0, 0)),
                self.keyGen("cr"): ("_moveHandler", (1, 0, 0)),
                self.keyGen("dl"): ("_moveHandler", (-1, -1, 0)),
                self.keyGen("dc"): ("_moveHandler", (0, -1, 0)),
                self.keyGen("dr"): ("_moveHandler", (1, -1, 0)),
                self.keyGen("uz"): ("_moveHandler", (0, 0, 1)),
                self.keyGen("dz"): ("_moveHandler", (0, 0, -1)),
                "activeController:wPos:x": ("_wPosHandlerX", None),
                "activeController:wPos:y": ("_wPosHandlerY", None),
                "activeController:wPos:z": ("_wPosHandlerZ", None),
                self.keyGen("wPos:x"): ("_wPosHandlerXUpdate", None),
                self.keyGen("wPos:y"): ("_wPosHandlerYUpdate", None),
                self.keyGen("wPos:z"): ("_wPosHandlerZUpdate", None),
                }

        self._xyJogStep = 10
        self._zJogStep = 10
        self._wPos = {}

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
        self.absoluteDistanceMode(False)
        self.moveTo(command="G00",
                    x=self._xyJogStep * values[0],
                    y=self._xyJogStep * values[1],
                    z=self._zJogStep * values[2],
                    f=10000  # TODO: Feed rates on jog.py
                    )

    def _wPosHandlerX(self, value):
        """ Called in response to an activeController:wPos:x event. """
        self._wPos["x"] = value
        self.publishOneByValue(self.keyGen("wPos:x"), value)

    def _wPosHandlerY(self, value):
        """ Called in response to an activeController:wPos:y event. """
        self._wPos["y"] = value
        self.publishOneByValue(self.keyGen("wPos:y"), value)

    def _wPosHandlerZ(self, value):
        """ Called in response to an activeController:wPos:z event. """
        self._wPos["z"] = value
        self.publishOneByValue(self.keyGen("wPos:z"), value)

    def _wPosHandlerXUpdate(self, value):
        """ Called in response to a local :wPos:x event. """
        if "x" in self._wPos and value == self._wPos["x"]:
            # Nothing to do.
            return
        self._updatedData.wPos = self._wPos

    def _wPosHandlerYUpdate(self, value):
        """ Called in response to a local :wPos:y event. """
        if "y" in self._wPos and value == self._wPos["y"]:
            # Nothing to do.
            return
        self._updatedData.wPos = self._wPos

    def _wPosHandlerZUpdate(self, value):
        """ Called in response to a local :wPos:z event. """
        if "z" in self._wPos and value == self._wPos["z"]:
            # Nothing to do.
            return
        self._updatedData.wPos = self._wPos

    def guiLayout(self):
        butW = 5
        butH = 1.5
        def txt(label: str, butW=butW, butH=butH) -> sg.Frame:
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

        coordW = 10
        coordH = 1
        def wCoord(key: str) -> sg.InputText:
            return sg.InputText(key,
                                key=self.keyGen(key),
                                size=(coordW, coordH),
                                justification="right",
                                pad=(0,0),
                                #background_color="grey",
                                )
       
        def mCoord(key: str) -> sg.InputText:
            return sg.InputText(key,
                                key="activeController:%s" % key,
                                size=(coordW, coordH),
                                justification="right",
                                pad=(0,0),
                                disabled=True,
                                background_color="grey",
                                )
        
        def fCoord(key: str) -> sg.InputText:
            return sg.InputText(key,
                                key="activeController:%s" % key,
                                size=(coordW / 2, coordH),
                                justification="right",
                                pad=(0,0),
                                disabled=True,
                                background_color="grey",
                                )
       
        pos = [
            [txt("mPos:", coordW / 2, coordH), mCoord("mPos:x"), mCoord("mPos:y"), mCoord("mPos:z")],
            [txt("wPos:", coordW / 2, coordH), wCoord("wPos:x"), wCoord("wPos:y"), wCoord("wPos:z")],
            ]
        feed = [
            [txt("Max feed:", coordW, coordH), fCoord("feedRateMax:x"),
                                               fCoord("feedRateMax:y"),
                                               fCoord("feedRateMax:z")],
            [txt("Feed accel:", coordW, coordH), fCoord("feedRateAccel:x"),
                                                 fCoord("feedRateAccel:y"),
                                                 fCoord("feedRateAccel:z")],
            [txt("Current feed:", coordW, coordH), fCoord("feedRate")]
            ]


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
                [sg.Column(pos),
                 sg.Column(feed),
                 sg.Stretch()
                 ],
                [sg.Column(layoutXY, pad=(0,0), size=(1,1)),
                 sg.Column(layoutZ, pad=(0,0), size=(1,1)),
                 sg.Stretch()
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
