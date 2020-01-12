from typing import Dict
from enum import Enum

from pygcode import block, GCodeLinearMove, GCodeRapidMove, GCodeArcMoveCW, GCodeArcMoveCCW, GCodeStraightProbe, GCodeCancelCannedCycle, GCodeIncrementalDistanceMode, GCodeAbsoluteDistanceMode, GCodeUseMillimeters, GCodeUseInches, GCodeFeedRate

class FlagState(Enum):
    UNSET = 0
    TRUE = 1
    FALSE = 2

class Command:
    _sequence: int = 0
    sequence: int = None
    gcode: Dict = None
    halt: bool = None
    pause: bool = None
    cancel: bool = None

    def __init__(self):
        self.sequence = Command._sequence
        Command._sequence += 1

class ConnectionState(Enum):
    UNKNOWN = 0
    NOT_CONNECTED = 1
    MISSING_RESOURCE = 2
    CONNECTING = 3
    CONNECTED = 4
    DISCONNECTING = 5
    FAIL = 6
    CLEANUP = 7

MODAL_GROUPS = {
        "motion": {
            "G00": GCodeRapidMove,
            "G01": GCodeLinearMove,
            "G02": GCodeArcMoveCW,
            "G03": GCodeArcMoveCCW,
            "G38.2": GCodeStraightProbe,
            "G38.3": GCodeStraightProbe,
            "G38.4": GCodeStraightProbe,
            "G38.5": GCodeStraightProbe,
            "G80": GCodeCancelCannedCycle
            },
        "coordSystem": {
            },
        "plane": {
            },
        "distance": {
            "G90": GCodeAbsoluteDistanceMode,
            "G91": GCodeIncrementalDistanceMode
            },
        "arkDistance": {
            },
        "feedRateMode": {
            },
        "units": {
            "G20": GCodeUseInches,
            "G21": GCodeUseMillimeters,
            },
        "cutterRadComp": {
            },
        "toolLength": {
            },
        "program": {
            },
        "spindle": {
        },
        "coolant": {
            }
        }

MODAL_COMMANDS = {
        b"G0": b"motion",
        b"G00": b"motion",
        b"G1": b"motion",
        b"G01": b"motion",
        b"G2": b"motion",
        b"G02": b"motion",
        b"G3": b"motion",
        b"G03": b"motion",
        b"G38.2": b"motion",
        b"G38.3": b"motion",
        b"G38.4": b"motion",
        b"G38.5": b"motion",
        b"G80": b"motion",
        b"G54": b"coordSystem",
        b"G55": b"coordSystem",
        b"G56": b"coordSystem",
        b"G57": b"coordSystem",
        b"G58": b"coordSystem",
        b"G59": b"coordSystem",
        b"G17": b"plane",
        b"G18": b"plane",
        b"G19": b"plane",
        b"G90": b"distance",
        b"G91": b"distance",
        b"G91.1": b"arkDistance",
        b"G93": b"feedRateMode",
        b"G94": b"feedRateMode",
        b"G20": b"units",
        b"G21": b"units",
        b"G40": b"cutterRadComp",
        b"G43.1": b"toolLength",
        b"G49": b"toolLength",
        b"M0": b"program",
        b"M1": b"program",
        b"M2": b"program",
        b"M30": b"program",
        b"M3": b"spindle",
        b"M4": b"spindle",
        b"M5": b"spindle",
        b"M7": b"coolant",
        b"M8": b"coolant",
        b"M9": b"coolant",
        # The next 3 are not strictly Modal groups but the fit well here,
        b"T": b"toolNumber",
        b"S": b"spindleSpeed",
        b"F": b"feedRate"
        }

class State:
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

    def __init__(self):
        self.machinePos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.workPos: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.workOffset: Dict = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.feedRate: int = 0
        self.feedOverrride: int = 100
        self.rapidOverrride: int = 100
        self.spindleRate: int = 0
        self.spindleOverride: int = 100
        self.limit: Dict = {"xu": False, "xl": False,
                            "yu": False, "yl": False,
                            "zu": False, "zl": False,
                            "au": False, "al": False,
                            "bu": False, "bl": False}
        self.probe: bool = False
        self.pause: bool = False
        self.pausePark: bool = False
        self.halt: bool = False
        self.door: bool = False
        self.resetComplete: bool = True
        self.pauseReason: List = []
        self.haltReason: List = []
        self.resetReason: List = [b"STARTUP"]

        self.gcodeModal: Dict = {}

        self.versionInfo: List = []  # Up to the controller how this is populated.

        self.eventFired: bool = False

    def __str__(self):
        output = ("machinePos x: {self.machinePos[x]} y: {self.machinePos[y]} "
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


    def setWorkOffset(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.workOffset["x"] = x
            self.workPos["x"] = self.machinePos["x"] - self.workOffset.get("x", 0)
        if y is not None:
            self.workOffset["y"] = y
            self.workPos["y"] = self.machinePos["y"] - self.workOffset.get("y", 0)
        if z is not None:
            self.workOffset["z"] = z
            self.workPos["z"] = self.machinePos["z"] - self.workOffset.get("z", 0)
        if a is not None:
            self.workOffset["a"] = a
            self.workPos["a"] = self.machinePos["a"] - self.workOffset.get("a", 0)
        if b is not None:
            self.workOffset["b"] = b
            self.workPos["b"] = self.machinePos["b"] - self.workOffset.get("b", 0)

    def setMachinePos(self, pos: Dict):
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

    def setWorkPos(self, pos: Dict):
        x = pos.get("x")
        y = pos.get("y")
        z = pos.get("z")
        a = pos.get("a")
        b = pos.get("b")
        if x is not None:
            self.workPos["x"] = x
            self.workPos["x"] = self.workPos["x"] + self.machineOffset.get("x", 0)
        if y is not None:
            self.workPos["y"] = y
            self.workPos["y"] = self.workPos["y"] + self.machineOffset.get("y", 0)
        if z is not None:
            self.workPos["z"] = z
            self.workPos["z"] = self.workPos["z"] + self.machineOffset.get("z", 0)
        if a is not None:
            self.workPos["a"] = a
            self.workPos["a"] = self.workPos["a"] + self.machineOffset.get("a", 0)
        if b is not None:
            self.workPos["b"] = b
            self.workPos["b"] = self.workPos["b"] + self.machineOffset.get("b", 0)


