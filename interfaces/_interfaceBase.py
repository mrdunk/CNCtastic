from enum import Enum
from typing import Dict

from pygcode import block, GCodeLinearMove, GCodeRapidMove, GCodeArcMoveCW, GCodeArcMoveCCW, GCodeStraightProbe, GCodeCancelCannedCycle, GCodeIncrementalDistanceMode, GCodeAbsoluteDistanceMode, GCodeUseMillimeters, GCodeUseInches, GCodeFeedRate

from coordinator.coordinator import _CoreComponent
from definitions import FlagState, State, InterfaceState


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

class _InterfaceBase(_CoreComponent):
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
                readyForPull: A boolean flag indicating this object has data ready to be pulled.
                status: The current state of this object. eg: Is it ready for use?
                state: A reference to the Coordinator's state object. Do not modify it here.
                _updatedData: Store desired changes to state here to be pulled later. """
        super().__init__(label)
        self.readyForPush: bool
        self.readyForPull: bool
        self.status: InterfaceState = InterfaceState.UNKNOWN
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
        raise NotImplementedError
        return InterfaceState.UNKNOWN

    def disconnect(self):
        """ Any cleanup tasks go here. """
        raise NotImplementedError
        return InterfaceState.UNKNOWN

    def service(self):
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        raise NotImplementedError

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

    def absoluteDistanceMode(self, *argv, **argkv):
        if "command" not in argkv:
            if len(argv) > 1:
                if isinstance(argv[1], bool):
                    if argv[1]:
                        argkv["command"] = "G90"
                    else:
                        argkv["command"] = "G91"
                else:
                    raise ValueError("Expected bool or \"command='G90'\" "
                                     "or \"command='G91'\" as paramiter."
                                     " Got: %s %s" % (argv[1], type(argv[1])))
            else:
                # No usable input at all. Let's default to Absolute distance.
                argkv["command"] = "G90"
        else:
            if argkv["command"] not in self.modalGroups["distance"]:
                # Add gcode definition to self.modalGroups.
                raise ValueError("Expected bool or \"command='G90'\" "
                                 "or \"command='G91'\" as paramiter.")

        self._gcodeCommand("distance", **argkv)

    def _gcodeCommand(self, modalGroup, **argkv):
        command = argkv["command"]
        del argkv["command"]

        if command not in self.modalGroups[modalGroup]:
            # Add gcode definition to self.modalGroups.
            raise ValueError(
                    "WARNING: gcode from modal group %s not supported: %s" %
                    (modalGroup, command))

        movetype = self.modalGroups[modalGroup][command]

        if self._updatedData.gcode is None:
            self._updatedData.gcode = block.Block()
        self._updatedData.gcode.gcodes.append(movetype(**argkv))
        self.readyForPull = True

        

