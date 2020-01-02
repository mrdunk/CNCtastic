from enum import Enum
from typing import Dict

from pygcode import block, GCodeLinearMove, GCodeRapidMove, GCodeArcMoveCW, GCodeArcMoveCCW, GCodeStraightProbe, GCodeCancelCannedCycle, GCodeIncrementalDistanceMode, GCodeAbsoluteDistanceMode, GCodeUseMillimeters, GCodeUseInches, GCodeFeedRate

from definitions import FlagState, State


class InterfaceState(Enum):
    UNKNOWN = 0
    STALE_DATA = 1
    UP_TO_DATE = 2
    FAIL = 3

class UpdateState:
    """ Data container representing changes to be made to the state of the system. """
    def __init__(self,
                 gcode: block.Block = None,
                 halt: FlagState = FlagState.UNSET,
                 pause: FlagState = FlagState.UNSET,
                 jog: FlagState = FlagState.UNSET):
        """
        Args:
            gcode: A pygcode Block object containing a single gcode line.
            halt: A boolean flag requesting all current tasks should stop.
            pause: A boolean flag requesting all current tasks should pause.
            TODO: reset flag. Others?
        """    
        self.gcode: block.Block = gcode
        self.halt: FlagState = halt
        self.pause: FlagState = pause
        self.jog: FlagState = jog

    def copy(self, target):
        """ Copy the data contains in this object to another UpdateState instance. """
        target.gcode = self.gcode
        target.halt = self.halt
        target.pause = self.pause

class _InterfaceBase:
    """ A base class for user input objects used for controlling the machine. """

    modalGroups = {
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
            "feedRate": {
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
            "spindle:": {
            },
            "coolant": {
                }
            }

    def __init__(self, label: str = ""):
        """ Args:
                label: A string identifying this object.
                readyForPush: A boolean flag indicating this object is ready to receive data.
                readyForPull: A boolean flag indicating this object has data reay to be pulled.
                status: The current state of this object. eg: Is it ready for use?
                ui: A windowing object for displaying the data contained here on screen.
                state: A reference to the Coordinator's state object. Do not modify it here.
                _updatedData: Store desired changes to state here to be pulled later. """
        self.label: str = label
        self.readyForPush: bool
        self.readyForPull: bool
        self.status: InterfaceState = InterfaceState.UNKNOWN
        self.ui: [] = []
        self.state: State = None
        self._updatedData: UpdateState = UpdateState()
    
    def push(self, data: State) -> bool:
        """ Send data to this object. """
        self.state = data
        self.status = InterfaceState.UP_TO_DATE

        # Since we copy the data object by reference, we don't have to come back
        # here to copy it in here again. self.state will remain up to datewithout
        # the copy.
        # The following switches off push updates from the Coordinator.
        self.readyForPush = False

        return True

    def pull(self) -> UpdateState:
        """ Get data from this object. """
        self.readyForPull = False
        
        # Return reference to the old self._updatedData and create a new (blank)
        # object for the next set of updates.
        command = self._updatedData
        self._updatedData = UpdateState()
        return command

    def connect(self):
        """ Any initialisation tasks go here. """
        assert False, "Undefined method"
        return InterfaceState.UNKNOWN

    def disconnect(self):
        """ Any cleanup tasks go here. """
        assert False, "Undefined method"
        return InterfaceState.UNKNOWN

    def service(self):
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        assert False, "Undefined method"

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
        if "command" not in argkv:
            argkv["command"] = "G01"

        feed = None
        if "f" in argkv:
            feed = argkv["f"]
            del argkv["f"]
        if "F" in argkv:
            feed = argkv["F"]
            del argkv["F"]

        self._gcodeCommand("motion", **argkv)
        if feed is not None:
            self._updatedData.gcode.gcodes.append(GCodeFeedRate(feed))

    def absoluteDistanceMode(self, **argkv):
        if "command" not in argkv:
            argkv["command"] = "G90"
        self._gcodeCommand("distance", **argkv)

    def _gcodeCommand(self, modalGroup, **argkv):
        command = argkv["command"]
        del argkv["command"]

        if command not in self.modalGroups[modalGroup]:
            print("WARNING: Unknown move type: %s" % command)
            return

        movetype = self.modalGroups[modalGroup][command]

        if self._updatedData.gcode is None:
            self._updatedData.gcode = block.Block()
        self._updatedData.gcode.gcodes.append(movetype(**argkv))
        self.readyForPull = True

        

