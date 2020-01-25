from typing import Dict, List, Callable

from definitions import MODAL_GROUPS, MODAL_COMMANDS


class StateMachineBase:
    PAUSE_REASONS = {b"USER_SW": "User initiated pause from terminal.",
                     b"USER_HW": "User initiated pause via HW button.",
                     b"DOOR_OPEN": "Door currently open.",
                     b"DOOR_CLOSED": "Door previously open.",
                     }
    HALT_REASONS = {b"USER_SW": "User initiated halt from terminal.",
                    b"USER_HW": "User initiated halt via HW button.",
                    b"UNKNOWN": "Unknown reason for halt."
                    }
    RESET_REASONS = {b"USER_SW": "User initiated reset from terminal.",
                     b"USER_HW": "User initiated reset via HW button.",
                     b"STARTUP": "Returning from power up.",
                     b"UNKNOWN": "Unknown reason for reset."
                    }

    machineProperties = [
            "machinePos",
            "machinePosMax",
            "machinePosMin",
            "workPos",
            "workOffset",
            "feedRate",
            "feedRateMax",
            "feedRateAccel",
            #"feedOverride",
            #"rapidOverride",
            "spindleRate",
            "spindleOverride",
            "limitX",
            "limitY",
            "limitZ",
            "limitA",
            "limitB",
            "probe",
            "pause",
            "parking",
            "halt",
            "door",
            ]

    def __init__(self, onUpdateCallback: Callable) -> None:
        self.onUpdateCallback = onUpdateCallback

        self.__machinePos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machinePosMax: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machinePosMin: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__workPos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__workOffset: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedRate: int = 0
        self.__feedRateMax: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedRateAccel: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedOverride: int = 100
        self.__rapidOverride: int = 100
        self.__spindleRate: int = 0
        self.__spindleOverride: int = 100
        self.__limitX: float = False
        self.__limitY: float = False
        self.__limitZ: float = False
        self.__limitA: float = False
        self.__limitB: float = False
        self.__probe: bool = False
        self.__pause: bool = False
        self.pauseReason: List = []
        self.__parking: bool = False
        self.__halt: bool = False
        self.haltReason: List = []
        self.__door: bool = False
        self.version: List[bytes] = []  # TODO Setter.

        self.gcodeModal: Dict = {}

        self.version: List = []  # Up to the controller how this is populated.
        self.machineIdentifier: List = []  # Up to the controller how this is populated.

        self.changesMade: bool = True

    def __str__(self) -> str:
        output = ("Pause: {self.pause}\tHalt: {self.halt}\n")
        output += ("machinePos x: {self.machinePos[x]} y: {self.machinePos[y]} "
                             "z: {self.machinePos[z]} a: {self.machinePos[a]} "
                             "b: {self.machinePos[b]}\r\n")
        if self.machinePos != self.workPos:
            output += ("workPos x: {self.workPos[x]} y: {self.workPos[y]} "
                               "z: {self.workPos[z]} a: {self.workPos[a]} "
                               "b: {self.workPos[b]}\r\n")
            output += ("workOffset x: {self.workOffset[x]} y: {self.workOffset[y]} "
                                  "z: {self.workOffset[z]} a: {self.workOffset[a]} "
                                  "b: {self.workOffset[b]}\r\n")
        output += "feedRate: {self.feedRate}\r\n"
        output += "gcodeModalGroups: {self.gcodeModal}\r\n"
        return output.format(self=self)

    def sync(self) -> None:
        """ Publish all machine properties. """
        for prop in self.machineProperties:
            value = getattr(self, prop)
            if type(prop) in ["number", "str"]:
                self.onUpdateCallback(prop, value)
            elif isinstance(value, dict):
                for subProp, subValue in value.items():
                    self.onUpdateCallback("%s:%s" % (prop, subProp), subValue)

    @property
    def workOffset(self) -> Dict[str, float]:
        return self.__workOffset

    @workOffset.setter
    def workOffset(self, pos: Dict) -> None:
        dataChanged = False
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            if self.__workOffset["x"] != x:
                dataChanged = True
                self.__workOffset["x"] = x
                self.workPos["x"] = self.machinePos["x"] - self.__workOffset.get("x", 0)
        if y is not None:
            if self.__workOffset["y"] != y:
                dataChanged = True
                self.__workOffset["y"] = y
                self.workPos["y"] = self.machinePos["y"] - self.__workOffset.get("y", 0)
        if z is not None:
            if self.__workOffset["z"] != z:
                dataChanged = True
                self.__workOffset["z"] = z
                self.workPos["z"] = self.machinePos["z"] - self.__workOffset.get("z", 0)
        if a is not None:
            if self.__workOffset["a"] != a:
                dataChanged = True
                self.__workOffset["a"] = a
                self.workPos["a"] = self.machinePos["a"] - self.__workOffset.get("a", 0)
        if b is not None:
            if self.__workOffset["b"] != b:
                dataChanged = True
                self.__workOffset["b"] = b
                self.workPos["b"] = self.machinePos["b"] - self.__workOffset.get("b", 0)

        if dataChanged:
            self.onUpdateCallback("workOffset:x", self.workOffset["x"])
            self.onUpdateCallback("workOffset:y", self.workOffset["y"])
            self.onUpdateCallback("workOffset:z", self.workOffset["z"])
            self.onUpdateCallback("workOffset:a", self.workOffset["a"])
            self.onUpdateCallback("workOffset:b", self.workOffset["b"])
            self.onUpdateCallback("workPos:x", self.workPos["x"])
            self.onUpdateCallback("workPos:y", self.workPos["y"])
            self.onUpdateCallback("workPos:z", self.workPos["z"])
            self.onUpdateCallback("workPos:a", self.workPos["a"])
            self.onUpdateCallback("workPos:b", self.workPos["b"])

    @property
    def machinePosMax(self) -> Dict[str, float]:
        return self.__machinePosMax

    @machinePosMax.setter
    def machinePosMax(self, pos: Dict) -> None:
        dataChanged = False
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            if self.machinePosMax["x"] != x:
                dataChanged = True
                self.machinePosMax["x"] = x
        if y is not None:
            if self.machinePosMax["y"] != y:
                dataChanged = True
                self.machinePosMax["y"] = y
        if z is not None:
            if self.machinePosMax["z"] != z:
                dataChanged = True
                self.machinePosMax["z"] = z
        if a is not None:
            if self.machinePosMax["a"] != a:
                dataChanged = True
                self.machinePosMax["a"] = a
        if b is not None:
            if self.machinePosMax["b"] != b:
                dataChanged = True
                self.machinePosMax["b"] = b
        
        if dataChanged:
            self.onUpdateCallback("machinePosMax:x", self.machinePosMax["x"])
            self.onUpdateCallback("machinePosMax:y", self.machinePosMax["y"])
            self.onUpdateCallback("machinePosMax:z", self.machinePosMax["z"])
            self.onUpdateCallback("machinePosMax:a", self.machinePosMax["a"])
            self.onUpdateCallback("machinePosMax:b", self.machinePosMax["b"])

    @property
    def machinePosMin(self) -> Dict[str, float]:
        return self.__machinePosMin

    @machinePosMin.setter
    def machinePosMin(self, pos: Dict) -> None:
        dataChanged = False
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            if self.machinePosMin["x"] != x:
                dataChanged = True
                self.machinePosMin["x"] = x
        if y is not None:
            if self.machinePosMin["y"] != y:
                dataChanged = True
                self.machinePosMin["y"] = y
        if z is not None:
            if self.machinePosMin["z"] != z:
                dataChanged = True
                self.machinePosMin["z"] = z
        if a is not None:
            if self.machinePosMin["a"] != a:
                dataChanged = True
                self.machinePosMin["a"] = a
        if b is not None:
            if self.machinePosMin["b"] != b:
                dataChanged = True
                self.machinePosMin["b"] = b
        
        if dataChanged:
            self.onUpdateCallback("machinePosMin:x", self.machinePosMin["x"])
            self.onUpdateCallback("machinePosMin:y", self.machinePosMin["y"])
            self.onUpdateCallback("machinePosMin:z", self.machinePosMin["z"])
            self.onUpdateCallback("machinePosMin:a", self.machinePosMin["a"])
            self.onUpdateCallback("machinePosMin:b", self.machinePosMin["b"])

    @property
    def machinePos(self) -> Dict[str, float]:
        return self.__machinePos

    @machinePos.setter
    def machinePos(self, pos: Dict) -> None:
        dataChanged = False
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            if self.machinePos["x"] != x:
                dataChanged = True
                self.machinePos["x"] = x
                self.workPos["x"] = self.machinePos["x"] - self.workOffset.get("x", 0)
        if y is not None:
            if self.machinePos["y"] != y:
                dataChanged = True
                self.machinePos["y"] = y
                self.workPos["y"] = self.machinePos["y"] - self.workOffset.get("y", 0)
        if z is not None:
            if self.machinePos["z"] != z:
                dataChanged = True
                self.machinePos["z"] = z
                self.workPos["z"] = self.machinePos["z"] - self.workOffset.get("z", 0)
        if a is not None:
            if self.machinePos["a"] != a:
                dataChanged = True
                self.machinePos["a"] = a
                self.workPos["a"] = self.machinePos["a"] - self.workOffset.get("a", 0)
        if b is not None:
            if self.machinePos["b"] != b:
                dataChanged = True
                self.machinePos["b"] = b
                self.workPos["b"] = self.machinePos["b"] - self.workOffset.get("b", 0)
        
        if dataChanged:
            self.onUpdateCallback("machinePos:x", self.machinePos["x"])
            self.onUpdateCallback("machinePos:y", self.machinePos["y"])
            self.onUpdateCallback("machinePos:z", self.machinePos["z"])
            self.onUpdateCallback("machinePos:a", self.machinePos["a"])
            self.onUpdateCallback("machinePos:b", self.machinePos["b"])
            self.onUpdateCallback("workPos:x", self.workPos["x"])
            self.onUpdateCallback("workPos:y", self.workPos["y"])
            self.onUpdateCallback("workPos:z", self.workPos["z"])
            self.onUpdateCallback("workPos:a", self.workPos["a"])
            self.onUpdateCallback("workPos:b", self.workPos["b"])

    @property
    def workPos(self) -> Dict[str, float]:
        return self.__workPos

    @workPos.setter
    def workPos(self, pos: Dict) -> None:
        dataChanged = False
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            if self.workPos["x"] != x:
                dataChanged = True
                self.workPos["x"] = x
                self.machinePos["x"] = self.workPos["x"] + self.__workOffset.get("x", 0)
        if y is not None:
            if self.workPos["y"] != y:
                dataChanged = True
                self.workPos["y"] = y
                self.machinePos["y"] = self.workPos["y"] + self.__workOffset.get("y", 0)
        if z is not None:
            if self.workPos["z"] != z:
                dataChanged = True
                self.workPos["z"] = z
                self.machinePos["z"] = self.workPos["z"] + self.__workOffset.get("z", 0)
        if a is not None:
            if self.workPos["a"] != a:
                dataChanged = True
                self.workPos["a"] = a
                self.machinePos["a"] = self.workPos["a"] + self.__workOffset.get("a", 0)
        if b is not None:
            if self.workPos["b"] != b:
                dataChanged = True
                self.workPos["b"] = b
                self.machinePos["b"] = self.workPos["b"] + self.__workOffset.get("b", 0)
        
        if dataChanged:
            self.onUpdateCallback("machinePos:x", self.machinePos["x"])
            self.onUpdateCallback("machinePos:y", self.machinePos["y"])
            self.onUpdateCallback("machinePos:z", self.machinePos["z"])
            self.onUpdateCallback("machinePos:a", self.machinePos["a"])
            self.onUpdateCallback("machinePos:b", self.machinePos["b"])
            self.onUpdateCallback("workPos:x", self.workPos["x"])
            self.onUpdateCallback("workPos:y", self.workPos["y"])
            self.onUpdateCallback("workPos:z", self.workPos["z"])
            self.onUpdateCallback("workPos:a", self.workPos["a"])
            self.onUpdateCallback("workPos:b", self.workPos["b"])

    @property
    def feedRate(self) -> float:
        return self.__feedRate

    @feedRate.setter
    def feedRate(self, feedRate: int) -> None:
        if self.__feedRate != feedRate:
            self.onUpdateCallback("feedRate", feedRate)
        self.__feedRate = feedRate

    @property
    def feedRateMax(self) -> Dict[str, int]:
        return self.__feedRateMax

    @feedRateMax.setter
    def feedRateMax(self, fr: Dict[str, int]) -> None:
        dataChanged = False
        x = fr.get("x")
        y = fr.get("y")
        z = fr.get("z")
        a = fr.get("a")
        b = fr.get("b")
        if x is not None:
            if self.feedRateMax["x"] != x:
                dataChanged = True
                self.feedRateMax["x"] = x
        if y is not None:
            if self.feedRateMax["y"] != y:
                dataChanged = True
                self.feedRateMax["y"] = y
        if z is not None:
            if self.feedRateMax["z"] != z:
                dataChanged = True
                self.feedRateMax["z"] = z
        if a is not None:
            if self.feedRateMax["a"] != a:
                dataChanged = True
                self.feedRateMax["a"] = a
        if b is not None:
            if self.feedRateMax["b"] != b:
                dataChanged = True
                self.feedRateMax["b"] = b
        
        if dataChanged:
            self.onUpdateCallback("feedRateMax:x", self.feedRateMax["x"])
            self.onUpdateCallback("feedRateMax:y", self.feedRateMax["y"])
            self.onUpdateCallback("feedRateMax:z", self.feedRateMax["z"])
            self.onUpdateCallback("feedRateMax:a", self.feedRateMax["a"])
            self.onUpdateCallback("feedRateMax:b", self.feedRateMax["b"])

    @property
    def feedRateAccel(self) -> Dict[str, int]:
        return self.__feedRateAccel

    @feedRateAccel.setter
    def feedRateAccel(self, fr: Dict[str, int]) -> None:
        dataChanged = False
        x = fr.get("x")
        y = fr.get("y")
        z = fr.get("z")
        a = fr.get("a")
        b = fr.get("b")
        if x is not None and self.feedRateAccel["x"] != x:
            dataChanged = True
            self.feedRateAccel["x"] = x
        if y is not None and self.feedRateAccel["y"] != y:
            dataChanged = True
            self.feedRateAccel["y"] = y
        if z is not None and self.feedRateAccel["z"] != z:
            dataChanged = True
            self.feedRateAccel["z"] = z
        if a is not None and self.feedRateAccel["a"] != a:
            dataChanged = True
            self.feedRateAccel["a"] = a
        if b is not None and self.feedRateAccel["b"] != b:
            dataChanged = True
            self.feedRateAccel["b"] = b
        
        if dataChanged:
            self.onUpdateCallback("feedRateAccel:x", self.feedRateAccel["x"])
            self.onUpdateCallback("feedRateAccel:y", self.feedRateAccel["y"])
            self.onUpdateCallback("feedRateAccel:z", self.feedRateAccel["z"])
            self.onUpdateCallback("feedRateAccel:a", self.feedRateAccel["a"])
            self.onUpdateCallback("feedRateAccel:b", self.feedRateAccel["b"])

    @property
    def feedOverride(self) -> float:
        return self.__feedOverride

    @feedOverride.setter
    def feedOverride(self, feedOverride: int) -> None:
        if self.__feedOverride != feedOverride:
            self.__feedOverride = feedOverride
            self.onUpdateCallback("feedOverride", self.feedOverride)

    @property
    def rapidOverride(self) -> float:
        return self.__rapidOverride

    @rapidOverride.setter
    def rapidOverride(self, rapidOverride: int) -> None:
        if self.__rapidOverride != rapidOverride:
            self.__rapidOverride = rapidOverride
            self.onUpdateCallback("rapidOverride", self.rapidOverride)

    @property
    def spindleRate(self) -> float:
        return self.__spindleRate

    @spindleRate.setter
    def spindleRate(self, spindleRate: int) -> None:
        if self.__spindleRate != spindleRate:
            self.__spindleRate = spindleRate
            self.onUpdateCallback("spindleRate", self.spindleRate)

    @property
    def spindleOverride(self) -> float:
        return self.__spindleOverride

    @spindleOverride.setter
    def spindleOverride(self, spindleOverride: int) -> None:
        if self.__spindleOverride != spindleOverride:
            self.__spindleOverride = spindleOverride
            self.onUpdateCallback("spindleOverride", self.spindleOverride)

    @property
    def limitX(self) -> float:
        return self.__limitX

    @limitX.setter
    def limitX(self, limitX: float) -> None:
        if self.__limitX != limitX:
            self.__limitX = limitX
            self.onUpdateCallback("limitX", self.limitX)

    @property
    def limitY(self) -> float:
        return self.__limitY

    @limitY.setter
    def limitY(self, limitY: float) -> None:
        if self.__limitY != limitY:
            self.__limitY = limitY
            self.onUpdateCallback("limitY", self.limitY)

    @property
    def limitZ(self) -> float:
        return self.__limitZ

    @limitZ.setter
    def limitZ(self, limitZ: float) -> None:
        if self.__limitZ != limitZ:
            self.__limitZ = limitZ
            self.onUpdateCallback("limitZ", self.limitZ)

    @property
    def limitA(self) -> float:
        return self.__limitA

    @limitA.setter
    def limitA(self, limitA: float) -> None:
        if self.__limitA != limitA:
            self.__limitA = limitA
            self.onUpdateCallback("limitA", self.limitA)

    @property
    def limitB(self) -> float:
        return self.__limitB

    @limitB.setter
    def limitB(self, limitB: float) -> None:
        if self.__limitB != limitB:
            self.__limitB = limitB
            self.onUpdateCallback("limitB", self.limitB)

    @property
    def probe(self) -> bool:
        return self.__probe

    @probe.setter
    def probe(self, probe: bool) -> None:
        if self.__probe != probe:
            self.__probe = probe
            self.onUpdateCallback("probe", self.probe)

    @property
    def pause(self) -> bool:
        return self.__pause

    @pause.setter
    def pause(self, pause: bool) -> None:
        if self.__pause != pause:
            self.__pause = pause
            self.onUpdateCallback("pause", self.pause)
            if pause == False:
                self.pauseReason.clear()
                self.onUpdateCallback("pauseReason", self.pauseReason)

    @property
    def parking(self) -> bool:
        return self.__parking

    @parking.setter
    def parking(self, parking: bool) -> None:
        if self.__parking != parking:
            self.__parking = parking
            self.onUpdateCallback("parking", self.parking)

    @property
    def halt(self) -> bool:
        return self.__halt

    @halt.setter
    def halt(self, halt: bool) -> None:
        if self.__halt != halt:
            self.__halt = halt
            self.onUpdateCallback("halt", self.halt)
            if halt == False:
                self.haltReason.clear()
                self.onUpdateCallback("haltReason", self.haltReason)

    @property
    def door(self) -> bool:
        return self.__door

    @door.setter
    def door(self, door: bool) -> None:
        if self.__door != door:
            self.__door = door
            self.onUpdateCallback("door", self.door)



class StateMachineGrbl(StateMachineBase):
    
    GRBL_STATUS_HEADERS = {b"MPos": "machinePos",
                           b"WPos": "workPos",
                           b"FS": "feedRate",    # Variable spindle.
                           b"F": "feedRate",     # Non variable spindle.
                           b"Pn": "inputPins",
                           b"WCO": "workCoordOffset",
                           b"Ov": "overrideValues",
                           b"Bf": "bufferState",
                           b"Ln": "lineNumber",
                           b"A": "accessoryState"
                           } 

    MACHINE_STATES = [
            b"Idle", b"Run", b"Hold", b"Jog", b"Alarm", b"Door", b"Check", b"Home", b"Sleep"]

    # Cheaper than global lookups
    MODAL_GROUPS = MODAL_GROUPS
    MODAL_COMMANDS = MODAL_COMMANDS

    def __init__(self, onUpdateCallback: Callable) -> None:
        super().__init__(onUpdateCallback)

    def parseIncoming(self, incoming: bytes) -> None:
        if incoming.startswith(b"error:"):
            print(b"ERROR:", incoming, b"TODO")
        elif incoming.startswith(b"ok"):
            assert False, "'ok' response should not have been passed to state machine."
        elif incoming.startswith(b"ALARM:"):
            self._parseIncomingAlarm(incoming)
        elif incoming.startswith(b"<"):
            self._parseIncomingStatus(incoming)
        elif incoming.startswith(b"["):
            self._parseIncomingFeedback(incoming)
        elif incoming.startswith(b"$"):
            self._parseSetting(incoming)
        elif incoming.startswith(b">"):
            self._parseStartup(incoming)
        elif incoming.startswith(b"Grbl "):
            self._parseStartup(incoming)
        else:
            print("Input not parsed: %s" % incoming)

    def _parseIncomingStatus(self, incoming: bytes) -> None:
        assert incoming.startswith(b"<") and incoming.endswith(b">")

        incoming = incoming.strip(b"<>")

        fields = incoming.split(b"|")
        
        machineState = fields[0]
        self._setState(machineState)

        for field in fields[1:]:
            identifier, value = field.split(b":")
            assert identifier in self.GRBL_STATUS_HEADERS
            if identifier in [b"MPos", b"WPos", b"WCO"]:
                self._setCoordinates(identifier, value)
            elif identifier == b"Ov":
                self._setOverrides(value)
            elif identifier == b"FS":
                feed, spindle = value.split(b",")
                self.feedRate = int(float(feed))
                self.spindleRate = int(float(spindle))
            elif identifier == b"F":
                self.feedRate = int(float(value))
            else:
                print("TODO. Unparsed status field: ", identifier, value)

        self.changesMade = True
    
    def _parseIncomingFeedbackModal(self, msg: bytes) -> None:
        """ Parse report on which modal option was last used for each group.
        Report comes fro one of 2 places:
        1. In response to a "$G" command, GRBL sends a G-code Parser State Message
           in the format:
           [GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0.0 S0]
        2. A Gcode line in the form "G0 X123 Y345 F2000" would update the "Motion"
           group (G0) and the Feed group (F2000).
        self.MODAL_COMMANDS maps these words to a group. eg: G0 is in the "motion" group.  """
        modals = msg.split(b" ")
        updateUnits = False
        for modal in modals:
            if modal in self.MODAL_GROUPS["units"]:
                modalGroup = self.MODAL_COMMANDS[modal]
                if self.gcodeModal[modalGroup] != modal:
                    # Grbl has changed from mm to inches or vice versa.
                    updateUnits = True

            if modal in self.MODAL_COMMANDS:
                modalGroup = self.MODAL_COMMANDS[modal]
                self.gcodeModal[modalGroup] = modal
            elif chr(modal[0]).encode('utf-8') in self.MODAL_COMMANDS:
                modalGroup = self.MODAL_COMMANDS[chr(modal[0]).encode('utf-8')]
                self.gcodeModal[modalGroup] = modal
            else:
                assert False, "Gcode word does not match any mmodal group: %s" % modal
        self.onUpdateCallback("gcodeModal", self.gcodeModal)

        assert not updateUnits, "TODO: Units have changed. Lots of things will need recalculated."

    def _parseIncomingFeedback(self, incoming: bytes) -> None:
        assert incoming.startswith(b"[") and incoming.endswith(b"]")

        incoming = incoming.strip(b"[]")

        msgType, msg = incoming.split(b":")

        if msgType == b"MSG":
            print(msgType, incoming, "TODO")
        elif msgType in [b"GC", b"sentGcode"]:
            self._parseIncomingFeedbackModal(msg)
        elif msgType == b"HLP":
            # Response to a "$" (print help) command. Only ever used by humans.
            pass
        elif msgType in [b"G54", b"G55", b"G56", b"G57", b"G58", b"G59", b"G28",
                         b"G30", b"G92", b"TLO", b"PRB"]:
            # Response to a "$#" command.
            print(msgType, incoming, "TODO")
        elif msgType == b"VER":
            if len(self.version) < 1:
                self.version.append(b"")
            self.version[0] = incoming
        elif msgType == b"OPT":
            while len(self.version) < 2:
                self.version.append(b"")
            self.version[1] = incoming
        elif msgType == b"echo":
            # May be enabled when building GRBL as a debugging option.
            pass
        else:
            assert False, "Unexpected feedback packet type: %s" % msgType


    def _parseIncomingAlarm(self, incoming: bytes) -> None:
        print("ALARM:", incoming)

    def _parseSetting(self, incoming: bytes) -> None:
        incoming = incoming.lstrip(b"$")
        setting, value = incoming.split(b"=")

        if setting == b"0":
            # Step pulse, microseconds
            pass
        elif setting == b"1":
            # Step idle delay, milliseconds
            pass
        elif setting == b"2":
            # Step port invert, mask
            pass
        elif setting == b"3":
            # Direction port invert, mask
            pass
        elif setting == b"4":
            # Step enable invert, boolean
            pass
        elif setting == b"5":
            # Limit pins invert, boolean
            pass
        elif setting == b"6":
            # Probe pin invert, boolean
            pass
        elif setting == b"10":
            # Status report, mask
            pass
        elif setting == b"11":
            # Junction deviation, mm
            pass
        elif setting == b"12":
            # Arc tolerance, mm
            pass
        elif setting == b"13":
            # Report inches, boolean
            pass
        elif setting == b"20":
            # Soft limits, boolean
            pass
        elif setting == b"21":
            # Hard limits, boolean
            pass
        elif setting == b"22":
            # Homing cycle, boolean
            pass
        elif setting == b"23":
            # Homing dir invert, mask
            pass
        elif setting == b"24":
            # Homing feed, mm/min
            pass
        elif setting == b"25":
            # Homing seek, mm/min
            pass
        elif setting == b"26":
            # Homing debounce, milliseconds
            pass
        elif setting == b"27":
            # Homing pull-off, mm
            pass
        elif setting == b"30":
            # Max spindle speed, RPM
            pass
        elif setting == b"31":
            # Min spindle speed, RPM
            pass
        elif setting == b"32":
            # Laser mode, boolean
            pass
        elif setting == b"100":
            # X steps/mm
            pass
        elif setting == b"101":
            # Y steps/mm
            pass
        elif setting == b"102":
            # Z steps/mm
            pass
        elif setting == b"110":
            # X Max rate, mm/min
            valueInt = int(float(value))
            self.feedRateMax = {"x": valueInt}
        elif setting == b"111":
            # Y Max rate, mm/min
            valueInt = int(float(value))
            self.feedRateMax = {"y": valueInt}
        elif setting == b"112":
            # Z Max rate, mm/min
            valueInt = int(float(value))
            self.feedRateMax = {"z": valueInt}
        elif setting == b"120":
            # X Acceleration, mm/sec^2
            valueInt = int(float(value))
            self.feedRateAccel = {"x": valueInt}
        elif setting == b"121":
            # Y Acceleration, mm/sec^2
            valueInt = int(float(value))
            self.feedRateAccel = {"y": valueInt}
        elif setting == b"122":
            # Z Acceleration, mm/sec^2
            valueInt = int(float(value))
            self.feedRateAccel = {"z": valueInt}
        elif setting == b"130":
            # X Max travel, mm
            pass
        elif setting == b"131":
            # Y Max travel, mm
            pass
        elif setting == b"132":
            # Z Max travel, mm
            pass
        else:
            assert False, "Unexpected setting: %s %s" % (setting, value)

    def _parseStartupLine(self, incoming: bytes) -> None:
        print("Startup:", incoming)
        assert incoming.startswith(b">") and incoming.endswith(b":ok")
        # This implies no alarms are active.
        print("Startup successful. TODO: Clear Alarm states.")

    def _parseStartup(self, incoming: bytes) -> None:
        print("GRBL Startup:", incoming)
    
    def _setOverrides(self, value: bytes) -> None:
        feedOverrride, rapidOverrride, spindleOverride = value.split(b",")
        feedOverrrideInt = int(float(feedOverrride))
        rapidOverrrideInt = int(float(rapidOverrride))
        spindleOverrideInt = int(float(spindleOverride))
        
        if 10 <= feedOverrrideInt <= 200:
            self.feedOverrride = feedOverrrideInt
        if rapidOverrrideInt in [100, 50, 20]:
            self.rapidOverrride = rapidOverrrideInt
        if 10 <= spindleOverrideInt <= 200:
            self.spindleOverride = spindleOverrideInt

    def _setCoordinates(self, identifier: bytes, value: bytes) -> None:
        if identifier == b"MPos":
            self.machinePos = self._parseCoordinates(value)
        elif identifier == b"WPos":
            self.workPos = self._parseCoordinates(value)
        elif identifier == b"WCO":
            self.workOffset = self._parseCoordinates(value)
        else:
            print("Invalid format: %s  Expected one of [MPos, WPos, WCO]" % identifier)

    def _parseCoordinates(self, string: bytes) -> Dict:
        parts = string.split(b",")
        if len(parts) < 3:
            print(string, parts)
            assert False, "Malformed coordinates: %s" % string
        coordinates = {}
        coordinates["x"] = float(parts[0])
        coordinates["y"] = float(parts[1])
        coordinates["z"] = float(parts[2])
        if len(coordinates) > 3:
            coordinates["a"] = float(parts[3])
        return coordinates

    def _setState(self, state: bytes) -> None:
        states = state.split(b":")
        assert len(states) <=2, "Invalid state: %s" % state

        if len(states) == 1:
            substate = None
        else:
            state, substate = states
            
        assert state in self.MACHINE_STATES, "Invalid state: %s" % state
        if state in [b"Idle", b"Run", b"Jog", b"Home"]:
            self.pause = False
            self.pausePark = False
            self.halt = False
            self.door = False
        elif state == b"Hold":
            # self.pausePark = False
            self.halt = False
            self.door = False
            self.pause = True
        elif state == b"Alarm":
            self.pause = False
            self.pausePark = False
            self.door = False
            self.halt = True
        elif state == b"Door":
            self.pause = False
            self.pausePark = False
            self.halt = False
            self.door = True
        elif state == b"Check":
            pass
        elif state == b"Sleep":
            pass


