from enum import Enum
from typing import Dict, Optional

from pygcode import block, GCodeFeedRate

from component import _ComponentBase
from definitions import FlagState, MODAL_GROUPS


class UpdateState:
    """ Data container representing changes to be made to the state of the system. """
    def __init__(self,
                 gcode: Optional[block.Block] = None,
                 wPos: Optional[Dict] = None,
                 halt: FlagState = FlagState.UNSET,
                 pause: FlagState = FlagState.UNSET,
                 jog: FlagState = FlagState.UNSET,
                 home: FlagState = FlagState.UNSET,
                 door: FlagState = FlagState.UNSET):
        """
        Args:
            gcode: A pygcode Block object containing a single gcode line.
            halt: A boolean flag requesting all current tasks should stop.
            pause: A boolean flag requesting all current tasks should pause.
            TODO: reset flag. Others?
        """    
        self.gcode: block.Block = gcode
        self.wPos: Dict[str:int] = wPos
        self.halt: FlagState = halt
        self.pause: FlagState = pause
        self.jog: FlagState = jog
        self.home: FlagState = home
        self.door: FlagState = door
        self.flags = ["halt", "pause", "jog", "home", "door"]

    def __str__(self):
        output = ""
        if self.gcode is None:
            output += "gcode: None\t"
        else:
            output += "gcode: {self.gcode.gcodes}\t"

        if self.wPos is None:
            output += "wPos: None\t"
        else:
            output += "wPos: {self.wPos}\t"

        output += "halt: {self.halt.name}\t"
        output += "pause: {self.pause.name}\t"
        output += "jog: {self.jog.name}\t"
        output += "home: {self.home.name}"
            
        return output.format(self=self)

class _InterfaceBase(_ComponentBase):
    """ A base class for user input objects used for controlling the machine. """

    modalGroups = MODAL_GROUPS  # Make a class reference to avoid expensive global lookup.

    def __init__(self, label: str = ""):
        """ Args:
                label: A string identifying this object.
                status: The current state of this object. eg: Is it ready for use?
                state: A reference to the Coordinator's state object. Do not modify it here.
                _updatedData: Store desired changes to state here to be pulled later. """
        super().__init__(label)
        self._updatedData: UpdateState = UpdateState()
    
    def update(self):
        for flag in self._updatedData.flags:
            attr = getattr(self._updatedData, flag)
            if attr != FlagState.UNSET:
                self.publishOneByValue("desiredState:%s" % flag, attr)
        if self._updatedData.gcode is not None:
            self.publishOneByValue("desiredState:newGcode", self._updatedData)
        
        # Clear self._updatedData 
        self._updatedData = UpdateState()
       
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
            if len(argv) > 0:
                if isinstance(argv[0], bool):
                    if argv[0]:
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
        

