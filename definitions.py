from typing import Dict
from enum import Enum

from pygcode import Machine

class FlagState(Enum):
    UNSET = 0
    TRUE = 1
    FALSE = 2

class State:
    """ Data container representing the current state of the system. """
    def __init__(self,
                 vm: Machine = None,
                 halt: bool = False,
                 pause: bool = False,
                 alarm: bool = False):
        """
        Args:
            vm: (Optional) Gcode Virtual Machine. This tracks expected machine state.
                https://github.com/fragmuffin/pygcode/wiki/Interpreting-gcode
            halt: A boolean flag requesting all current tasks should stop.
            pause: A boolean flag requesting all current tasks should pause.
            alarm: A boolean flag.
            TODO: Should alarm be an Enum of possible states?
        """    
        self.latestSequence: int = 0
        self.vm: Machine = vm
        self.halt: bool = halt
        self.pause: bool = pause
        self.alarm: bool = alarm

        self.physical = {
                "motion": {},
                "coordinate": {},
                "plane": {},
                "distance": {},
                "arkIJKDistance": {},
                "feedRateMode": {},
                "feedRate": 0,
                "units": {},
                "cutterRadius"
                "toolLen": {},
                "toolNumber": 0,
                "program": {},
                "spindleState": {},
                "spindleSpeed": 0,
                "coolant": {},
                "coordinates": {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
                }

class Command:
    _latestSequence: int = 0
    sequence: int = None
    gcode: Dict = None
    halt: bool = None
    pause: bool = None
    cancel: bool = None

    def __init__(self):
        self.sequence = Command._latestSequence
        Command._latestSequence += 1

class Response:
    sequence: int = 0
    def __init__(self, sequence):
        self.sequence = sequence

