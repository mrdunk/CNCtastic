""" Pluging providing control of some aspect of the active controller. """

from typing import Dict, Optional, Union, Callable, cast

from pygcode import block, GCodeFeedRate     # type: ignore

from component import _ComponentBase
from definitions import FlagState, MODAL_GROUPS


class UpdateState:
    """ Data container representing changes to be made to the state of the system. """
    def __init__(self) -> None:
        self.gcode: Optional[block.Block] = None
        self.halt: FlagState = FlagState.UNSET
        self.pause: FlagState = FlagState.UNSET
        self.jog: FlagState = FlagState.UNSET
        self.home: FlagState = FlagState.UNSET
        self.door: FlagState = FlagState.UNSET
        self.flags = ["halt", "pause", "jog", "home", "door"]

    def __str__(self) -> str:
        output = ""
        if self.gcode is None:
            output += "gcode: None\t"
        else:
            output += "gcode: {self.gcode.gcodes}\t"

        output += "halt: {self.halt.name}\t"
        output += "pause: {self.pause.name}\t"
        output += "jog: {self.jog.name}\t"
        output += "home: {self.home.name}"

        return output.format(self=self)

class _InterfaceBase(_ComponentBase):
    """ A base class for user input objects used for controlling the machine. """

    # Type of component. Used by the plugin loader.
    plugin_type = "interface"

    # Make a class reference to avoid expensive global lookup.
    modal_groups = cast(Dict[str, Dict[str, Callable]], MODAL_GROUPS)

    def __init__(self, label: str = "") -> None:
        """ Args:
                label: A string identifying this object. """
        super().__init__(label)
        self._updated_data: UpdateState = UpdateState()

    def update(self) -> None:
        """ Act on any events destined for this component.
            Called by the coordinator. """
        for flag in self._updated_data.flags:
            attr = getattr(self._updated_data, flag)
            if attr != FlagState.UNSET:
                self.publish_one_by_value("desiredState:%s" % flag, attr)
        if self._updated_data.gcode is not None:
            self.publish_one_by_value("desiredState:newGcode", self._updated_data)

        # Clear self._updated_data
        self._updated_data = UpdateState()

    def move_to(self, **argkv: Union[str, float]) -> None:
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

        self._gcode_command("motion", **argkv)

        assert self._updated_data.gcode is not None, "self._updated_data.gcode not set yet."

        if feed is not None:
            self._updated_data.gcode.gcodes.append(GCodeFeedRate(feed))

    def g92_offsets(self, **argkv: Union[str, float]) -> None:
        """ Set work position offset.
        http://linuxcnc.org/docs/2.6/html/gcode/coordinates.html#cha:coordinate-system
        """
        argkv["command"] = "G92"

        self._gcode_command("non_modal", **argkv)

        assert self._updated_data.gcode is not None, "self._updated_data.gcode not set yet."


    def absolute_distance_mode(self, *argv: bool, **argkv: Union[str, float]) -> None:
        """ Switch between "G90" and "G91" distance modes. """
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
            if argkv["command"] not in self.modal_groups["distance"]:
                # Add gcode definition to self.modal_groups.
                raise ValueError("Expected bool or \"command='G90'\" "
                                 "or \"command='G91'\" as paramiter.")

        self._gcode_command("distance", **argkv)

    def _gcode_command(self, modal_group: str, **argkv: Union[str, float]) -> None:
        command = cast(str, argkv["command"])
        del argkv["command"]

        if command not in self.modal_groups[modal_group]:
            # Add gcode definition to self.modal_groups.
            raise ValueError(
                "WARNING: gcode from modal group %s not supported: %s" %
                (modal_group, command))

        gcode_word = self.modal_groups[modal_group][command]

        if self._updated_data.gcode is None:
            self._updated_data.gcode = block.Block()
        self._updated_data.gcode.gcodes.append(gcode_word(**argkv))
        print("###", self._updated_data.gcode.gcodes)
