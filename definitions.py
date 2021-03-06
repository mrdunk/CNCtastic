""" Definitions that are called from everywhere throughout the codebase. """

from enum import Enum

from pygcode import (GCodeLinearMove, GCodeRapidMove, GCodeArcMoveCW,
                     GCodeArcMoveCCW, GCodeStraightProbe, GCodeCancelCannedCycle,
                     GCodeIncrementalDistanceMode, GCodeAbsoluteDistanceMode,
                     GCodeUseMillimeters, GCodeUseInches,
                     GCodeCoordSystemOffset, GCodeResetCoordSystemOffset,
                     GCodeRestoreCoordSystemOffset)


class ConnectionState(Enum):
    """ Connection state of one of the controller components.
    Used extensively by _ControllerBase and it's derivatives."""
    UNKNOWN = 0
    NOT_CONNECTED = 1
    MISSING_RESOURCE = 2
    BLOCKED = 3
    CONNECTING = 4
    CONNECTED = 5
    DISCONNECTING = 6
    FAIL = 7
    CLEANUP = 8

# Mapping of modal groups to the individual gcode commands they contain.
MODAL_GROUPS = {
    # "G" codes
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
    "plane_selection": {
        },
    "distance": {
        "G90": GCodeAbsoluteDistanceMode,
        "G91": GCodeIncrementalDistanceMode
        },
    "arc_ijk_distance": {
        },
    "feed_rate_mode": {
        },
    "units": {
        "G20": GCodeUseInches,
        "G21": GCodeUseMillimeters,
        },
    "cutter_diameter_comp": {
        },
    "tool_length_offset": {
        },
    "canned_cycles_return": {
        },
    "coordinate_system": {
        },
    "control_mode": {
        },
    "spindle_speed_mode": {
        },
    "lathe_diameter": {
        },

    # "M" codes
    "stopping": {
        },
    "spindle": {
        },
    "coolant": {
        },
    "override_switches": {
        },
    "user_defined": {
        },

    # Other
    "non_modal": {
        "G92": GCodeCoordSystemOffset,
        "G92.1": GCodeResetCoordSystemOffset,
        "G92.2": GCodeResetCoordSystemOffset,
        "G92.3": GCodeRestoreCoordSystemOffset,
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
    b"G54": b"coordinate_system",
    b"G55": b"coordinate_system",
    b"G56": b"coordinate_system",
    b"G57": b"coordinate_system",
    b"G58": b"coordinate_system",
    b"G59": b"coordinate_system",
    b"G17": b"plane_selection",
    b"G18": b"plane_selection",
    b"G19": b"plane_selection",
    b"G90": b"distance",                # Absolute
    b"G91": b"distance",                # Incremental
    b"G91.1": b"arc_ijk_distance",
    b"G93": b"feed_rate_mode",          # 1/time
    b"G94": b"feed_rate_mode",          # units/min
    b"G20": b"units",                   # Inches
    b"G21": b"units",                   # mm
    b"G40": b"cutter_diameter_comp",
    b"G43.1": b"tool_length_offset",
    b"G49": b"tool_length_offset",
    b"G61": b"path_control_mode",
    b"G61.1": b"path_control_mode",
    b"G64": b"path_control_mode",
    b"M0": b"stopping",
    b"M00": b"stopping",
    b"M1": b"stopping",
    b"M01": b"stopping",
    b"M2": b"stopping",
    b"M02": b"stopping",
    b"M30": b"stopping",
    b"M3": b"spindle",
    b"M03": b"spindle",
    b"M4": b"spindle",
    b"M04": b"spindle",
    b"M5": b"spindle",
    b"M05": b"spindle",
    b"M19": b"spindle",
    b"G96": b"spindle",
    b"G97": b"spindle",
    b"M7": b"coolant",
    b"M07": b"coolant",
    b"M8": b"coolant",
    b"M08": b"coolant",
    b"M9": b"coolant",
    b"M09": b"coolant",
    # The next 3 are not strictly Modal groups but the fit well here,
    b"F": b"feed_rate",
    b"S": b"spindle_speed",
    b"T": b"tool",
    }
