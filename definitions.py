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

# Mapping of modal groups to the individual gcode commands they contain.
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

# Map individual gcode commands to the modal groups they belong to.
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

