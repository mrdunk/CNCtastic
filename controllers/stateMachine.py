from typing import Dict

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

    def __init__(self, onUpdateCallback) -> None:
        self.onUpdateCallback = onUpdateCallback

        self.__machinePos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machinePosMax: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machinePosMin: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__workPos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__workOffset: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedRate: int = 0
        self.__feedRateMax: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedRateAccel: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feedOverrride: int = 100
        self.__rapidOverrride: int = 100
        self.__spindleRate: int = 0
        self.__spindleOverride: int = 100
        self.__limitX: bool = False
        self.__limitY: bool = False
        self.__limitZ: bool = False
        self.__limitA: bool = False
        self.__limitB: bool = False
        self.__limitXMax: bool = False
        self.__limitYMax: bool = False
        self.__limitZMax: bool = False
        self.__limitAMax: bool = False
        self.__limitBMax: bool = False
        self.__probe: bool = False
        self.__pause: bool = False
        self.pauseReason: List = []
        self.__parking: bool = False
        self.__halt: bool = False
        self.haltReason: List = []
        self.__door: bool = False

        self.gcodeModal: Dict = {}

        self.version: List = []  # Up to the controller how this is populated.
        self.machineIdentifier: List = []  # Up to the controller how this is populated.

        self.changesMade: bool = True

    def __str__(self):
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

    @property
    def workOffset(self):
        return self.__workOffset

    @workOffset.setter
    def workOffset(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.__workOffset["x"] = x
            self.workPos["x"] = self.machinePos["x"] - self.__workOffset.get("x", 0)
        if y is not None:
            self.__workOffset["y"] = y
            self.workPos["y"] = self.machinePos["y"] - self.__workOffset.get("y", 0)
        if z is not None:
            self.__workOffset["z"] = z
            self.workPos["z"] = self.machinePos["z"] - self.__workOffset.get("z", 0)
        if a is not None:
            self.__workOffset["a"] = a
            self.workPos["a"] = self.machinePos["a"] - self.__workOffset.get("a", 0)
        if b is not None:
            self.__workOffset["b"] = b
            self.workPos["b"] = self.machinePos["b"] - self.__workOffset.get("b", 0)

        self.onUpdateCallback("wOffset:x", self.workOffset["x"])
        self.onUpdateCallback("wOffset:y", self.workOffset["y"])
        self.onUpdateCallback("wOffset:z", self.workOffset["z"])
        self.onUpdateCallback("wOffset:a", self.workOffset["a"])
        self.onUpdateCallback("wOffset:b", self.workOffset["b"])
        self.onUpdateCallback("wPos:x", self.workPos["x"])
        self.onUpdateCallback("wPos:y", self.workPos["y"])
        self.onUpdateCallback("wPos:z", self.workPos["z"])
        self.onUpdateCallback("wPos:a", self.workPos["a"])
        self.onUpdateCallback("wPos:b", self.workPos["b"])

    @property
    def machinePosMax(self):
        return self.__machinePosMax

    @machinePosMax.setter
    def machinePosMax(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.machinePosMax["x"] = x
        if y is not None:
            self.machinePosMax["y"] = y
        if z is not None:
            self.machinePosMax["z"] = z
        if a is not None:
            self.machinePosMax["a"] = a
        if b is not None:
            self.machinePosMax["b"] = b
        
        self.onUpdateCallback("machinePosMax:x", self.machinePosMax["x"])
        self.onUpdateCallback("machinePosMax:y", self.machinePosMax["y"])
        self.onUpdateCallback("machinePosMax:z", self.machinePosMax["z"])
        self.onUpdateCallback("machinePosMax:a", self.machinePosMax["a"])
        self.onUpdateCallback("machinePosMax:b", self.machinePosMax["b"])

    @property
    def machinePosMin(self):
        return self.__machinePosMin

    @machinePosMin.setter
    def machinePosMin(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.machinePosMin["x"] = x
        if y is not None:
            self.machinePosMin["y"] = y
        if z is not None:
            self.machinePosMin["z"] = z
        if a is not None:
            self.machinePosMin["a"] = a
        if b is not None:
            self.machinePosMin["b"] = b
        
        self.onUpdateCallback("machinePosMin:x", self.machinePosMin["x"])
        self.onUpdateCallback("machinePosMin:y", self.machinePosMin["y"])
        self.onUpdateCallback("machinePosMin:z", self.machinePosMin["z"])
        self.onUpdateCallback("machinePosMin:a", self.machinePosMin["a"])
        self.onUpdateCallback("machinePosMin:b", self.machinePosMin["b"])

    @property
    def machinePos(self):
        return self.__machinePos

    @machinePos.setter
    def machinePos(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.machinePos["x"] = x
            self.workPos["x"] = self.machinePos["x"] - self.workOffset.get("x", 0)
        if y is not None:
            self.machinePos["y"] = y
            self.workPos["y"] = self.machinePos["y"] - self.workOffset.get("y", 0)
        if z is not None:
            self.machinePos["z"] = z
            self.workPos["z"] = self.machinePos["z"] - self.workOffset.get("z", 0)
        if a is not None:
            self.machinePos["a"] = a
            self.workPos["a"] = self.machinePos["a"] - self.workOffset.get("a", 0)
        if b is not None:
            self.machinePos["b"] = b
            self.workPos["b"] = self.machinePos["b"] - self.workOffset.get("b", 0)
        
        self.onUpdateCallback("mPos:x", self.machinePos["x"])
        self.onUpdateCallback("mPos:y", self.machinePos["y"])
        self.onUpdateCallback("mPos:z", self.machinePos["z"])
        self.onUpdateCallback("mPos:a", self.machinePos["a"])
        self.onUpdateCallback("mPos:b", self.machinePos["b"])
        self.onUpdateCallback("wPos:x", self.workPos["x"])
        self.onUpdateCallback("wPos:y", self.workPos["y"])
        self.onUpdateCallback("wPos:z", self.workPos["z"])
        self.onUpdateCallback("wPos:a", self.workPos["a"])
        self.onUpdateCallback("wPos:b", self.workPos["b"])

    @property
    def workPos(self):
        return self.__workPos

    @workPos.setter
    def workPos(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.workPos["x"] = x
            self.workPos["x"] = self.workPos["x"] + self.__machineOffset.get("x", 0)
        if y is not None:
            self.workPos["y"] = y
            self.workPos["y"] = self.workPos["y"] + self.__machineOffset.get("y", 0)
        if z is not None:
            self.workPos["z"] = z
            self.workPos["z"] = self.workPos["z"] + self.__machineOffset.get("z", 0)
        if a is not None:
            self.workPos["a"] = a
            self.workPos["a"] = self.workPos["a"] + self.__machineOffset.get("a", 0)
        if b is not None:
            self.workPos["b"] = b
            self.workPos["b"] = self.workPos["b"] + self.__machineOffset.get("b", 0)
        
        self.onUpdateCallback("mPos:x", self.machinePos["x"])
        self.onUpdateCallback("mPos:y", self.machinePos["y"])
        self.onUpdateCallback("mPos:z", self.machinePos["z"])
        self.onUpdateCallback("mPos:a", self.machinePos["a"])
        self.onUpdateCallback("mPos:b", self.machinePos["b"])
        self.onUpdateCallback("wPos:x", self.workPos["x"])
        self.onUpdateCallback("wPos:y", self.workPos["y"])
        self.onUpdateCallback("wPos:z", self.workPos["z"])
        self.onUpdateCallback("wPos:a", self.workPos["a"])
        self.onUpdateCallback("wPos:b", self.workPos["b"])

    @property
    def feedRate(self):
        return self.__feedRate

    @feedRate.setter
    def feedRate(self, feedRate: int):
        self.__feedRate = feedRate
        self.onUpdateCallback("feedRate", self.feedRate)

    @property
    def feedRateMax(self):
        return self.__feedRateMax

    @feedRateMax.setter
    def feedRateMax(self, fr: Dict):
        x = fr.get("x")
        y = fr.get("y")
        z = fr.get("z")
        a = fr.get("a")
        b = fr.get("b")
        if x is not None:
            self.feedRateMax["x"] = x
        if y is not None:
            self.feedRateMax["y"] = y
        if z is not None:
            self.feedRateMax["z"] = z
        if a is not None:
            self.feedRateMax["a"] = a
        if b is not None:
            self.feedRateMax["b"] = b
        
        self.onUpdateCallback("feedRateMax:x", self.feedRateMax["x"])
        self.onUpdateCallback("feedRateMax:y", self.feedRateMax["y"])
        self.onUpdateCallback("feedRateMax:z", self.feedRateMax["z"])
        self.onUpdateCallback("feedRateMax:a", self.feedRateMax["a"])
        self.onUpdateCallback("feedRateMax:b", self.feedRateMax["b"])

    @property
    def feedRateAccel(self):
        return self.__feedRateAccel

    @feedRateAccel.setter
    def feedRateAccel(self, fr: Dict):
        x = fr.get("x")
        y = fr.get("y")
        z = fr.get("z")
        a = fr.get("a")
        b = fr.get("b")
        if x is not None:
            self.feedRateAccel["x"] = x
        if y is not None:
            self.feedRateAccel["y"] = y
        if z is not None:
            self.feedRateAccel["z"] = z
        if a is not None:
            self.feedRateAccel["a"] = a
        if b is not None:
            self.feedRateAccel["b"] = b
        
        self.onUpdateCallback("feedRateAccel:x", self.feedRateAccel["x"])
        self.onUpdateCallback("feedRateAccel:y", self.feedRateAccel["y"])
        self.onUpdateCallback("feedRateAccel:z", self.feedRateAccel["z"])
        self.onUpdateCallback("feedRateAccel:a", self.feedRateAccel["a"])
        self.onUpdateCallback("feedRateAccel:b", self.feedRateAccel["b"])

    @property
    def feedOverride(self):
        return self.__feedOverride

    @feedOverride.setter
    def feedOverride(self, feedOverride: int):
        self.__feedOverride = feedOverride
        self.onUpdateCallback("feedOverride", self.feedOverride)

    @property
    def rapidOverride(self):
        return self.__rapidOverride

    @rapidOverride.setter
    def rapidOverride(self, rapidOverride: int):
        self.__rapidOverride = rapidOverride
        self.onUpdateCallback("rapidOverride", self.rapidOverride)

    @property
    def spindleRate(self):
        return self.__spindleRate

    @spindleRate.setter
    def spindleRate(self, spindleRate: int):
        self.__spindleRate = spindleRate
        self.onUpdateCallback("spindleRate", self.spindleRate)

    @property
    def spindleOverride(self):
        return self.__spindleOverride

    @spindleOverride.setter
    def spindleOverride(self, spindleOverride: int):
        self.__spindleOverride = spindleOverride
        self.onUpdateCallback("spindleOverride", self.spindleOverride)

    @property
    def limitX(self):
        return self.__limitX

    @limitX.setter
    def limitX(self, limitX: Dict):
        self.__limitX = limitX
        self.onUpdateCallback("limitX", self.limitX)

    @property
    def limitY(self):
        return self.__limitY

    @limitY.setter
    def limitY(self, limitY: Dict):
        self.__limitY = limitY
        self.onUpdateCallback("limitY", self.limitY)

    @property
    def limitZ(self):
        return self.__limitZ

    @limitZ.setter
    def limitZ(self, limitZ: Dict):
        self.__limitZ = limitZ
        self.onUpdateCallback("limitZ", self.limitZ)

    @property
    def limitA(self):
        return self.__limitA

    @limitA.setter
    def limitA(self, limitA: Dict):
        self.__limitA = limitA
        self.onUpdateCallback("limitA", self.limitA)

    @property
    def limitB(self):
        return self.__limitB

    @limitB.setter
    def limitB(self, limitB: Dict):
        self.__limitB = limitB
        self.onUpdateCallback("limitB", self.limitB)

    @property
    def limitXMax(self):
        return self.__limitXMax

    @limitXMax.setter
    def limitXMax(self, limitXMax: Dict):
        self.__limitXMax = limitXMax
        self.onUpdateCallback("limitXMax", self.limitXMax)

    @property
    def limitYMax(self):
        return self.__limitYMax

    @limitYMax.setter
    def limitYMax(self, limitYMax: Dict):
        self.__limitYMax = limitYMax
        self.onUpdateCallback("limitYMax", self.limitYMax)

    @property
    def limitZMax(self):
        return self.__limitZMax

    @limitZMax.setter
    def limitZMax(self, limitZMax: Dict):
        self.__limitZMax = limitZMax
        self.onUpdateCallback("limitZMax", self.limitZMax)

    @property
    def limitAMax(self):
        return self.__limitAMax

    @limitAMax.setter
    def limitAMax(self, limitAMax: Dict):
        self.__limitAMax = limitAMax
        self.onUpdateCallback("limitAMax", self.limitAMax)

    @property
    def limitBMax(self):
        return self.__limitBMax

    @limitBMax.setter
    def limitBMax(self, limitBMax: Dict):
        self.__limitBMax = limitBMax
        self.onUpdateCallback("limitBMax", self.limitBMax)

    @property
    def probe(self):
        return self.__probe

    @probe.setter
    def probe(self, probe: Dict):
        self.__probe = probe
        self.onUpdateCallback("probe", self.probe)

    @property
    def pause(self):
        return self.__pause

    @pause.setter
    def pause(self, pause: Dict):
        self.__pause = pause
        self.onUpdateCallback("pause", self.pause)
        if pause == False:
            self.pauseReason.clear()
            self.onUpdateCallback("pauseReason", self.pauseReason)

    @property
    def parking(self):
        return self.__parking

    @parking.setter
    def parking(self, parking: Dict):
        self.__parking = parking
        self.onUpdateCallback("parking", self.parking)

    @property
    def halt(self):
        return self.__halt

    @halt.setter
    def halt(self, halt: Dict):
        self.__halt = halt
        self.onUpdateCallback("halt", self.halt)
        if halt == False:
            self.haltReason.clear()
            self.onUpdateCallback("haltReason", self.haltReason)

    @property
    def door(self):
        return self.__door

    @door.setter
    def door(self, door: Dict):
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

    def __init__(self, onUpdateCallback):
        super().__init__(onUpdateCallback)

    def parseIncoming(self, incoming):
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

    def _parseIncomingStatus(self, incoming):
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
    
    def _parseIncomingFeedbackModal(self, msg):
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

    def _parseIncomingFeedback(self, incoming):
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
            if len(self.status.version) < 1:
                self.status.version.append(b"")
            self.status.version[0] = incoming
        elif msgType == b"OPT":
            while len(self.status.version) < 2:
                self.status.version.append(b"")
            self.status.version[1] = (msgType, incoming)
        elif msgType == b"echo":
            # May be enabled when building GRBL as a debugging option.
            pass
        else:
            assert False, "Unexpected feedback packet type: %s" % msgType


    def _parseIncomingAlarm(self, incoming):
        print("ALARM:", incoming)

    def _parseSetting(self, incoming):
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
            value = int(float(value))
            self.feedRateMax = {"x": value}
        elif setting == b"111":
            # Y Max rate, mm/min
            value = int(float(value))
            self.feedRateMax = {"y": value}
        elif setting == b"112":
            # Z Max rate, mm/min
            value = int(float(value))
            self.feedRateMax = {"z": value}
        elif setting == b"120":
            # X Acceleration, mm/sec^2
            value = int(float(value))
            self.feedRateAccel = {"x": value}
        elif setting == b"121":
            # Y Acceleration, mm/sec^2
            value = int(float(value))
            self.feedRateAccel = {"y": value}
        elif setting == b"122":
            # Z Acceleration, mm/sec^2
            value = int(float(value))
            self.feedRateAccel = {"z": value}
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

    def _parseStartupLine(self, incoming):
        print("Startup:", incoming)
        assert incoming.startswith(b">") and incomming.endswith(b":ok")
        # This implies no alarms are active.
        print("Startup successful. TODO: Clear Alarm states.")

    def _parseStartup(self, incoming):
        print("GRBL Startup:", incoming)
    
    def _setOverrides(self, value):
        feedOverrride, rapidOverrride, spindleOverride = value.split(b",")
        feedOverrride = int(float(feedOverrride))
        rapidOverrride = int(float(rapidOverrride))
        spindleOverride = int(float(spindleOverride))
        
        if 10 <= feedOverrride <= 200:
            self.feedOverrride = feedOverrride
        if rapidOverrride in [100, 50, 20]:
            self.rapidOverrride = rapidOverrride
        if 10 <= spindleOverride <= 200:
            self.spindleOverride = spindleOverride

    def _setCoordinates(self, identifier, value):
        if identifier == b"MPos":
            self.machinePos = self._parseCoordinates(value)
        elif identifier == b"WPos":
            self.workPos = self._parseCoordinates(value)
        elif identifier == b"WCO":
            self.workOffset = self._parseCoordinates(value)
        else:
            print("Invalid format: %s  Expected one of [MPos, WPos]" % posId)

    def _parseCoordinates(self, string) -> Dict:
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

    def _setState(self, state):
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


