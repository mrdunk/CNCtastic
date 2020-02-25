""" Plugin providing interface to control of some aspect of the active controller. """

from typing import Dict, Optional, Union, cast, Any

from pygcode import block, GCodeFeedRate, GCode

from component import _ComponentBase
from definitions import FlagState, MODAL_GROUPS


class _InterfaceBase(_ComponentBase):
    """ A base class for user input objects used for controlling the machine. """

    # Type of component. Used by the plugin loader.
    plugin_type = "interface"

    # Make a class reference to avoid expensive global lookup.
    modal_groups = cast(Dict[str, Dict[str, GCode]], MODAL_GROUPS)

    def move_relative(self, **argkv: Union[str, float]) -> None:
        """ Move the machine head relative to it's current position.
        Note this may or may not be translated to gcode by the controller later
        depending on the controller's functionality.
        Args:
            argkv: A dict containing one or more of the following parameters:
                command: The gcode command as a string. Defaults to "G01".
                x: The x coordinate.
                y: The y coordinate.
                z: The z coordinate.
                f: The feed rate.
        """
        self.publish_one_by_value("command:move_relative", argkv)

    def move_absolute(self, **argkv: Union[str, float]) -> None:
        """ Move the machine head to a absolute position.
        Note this may or may not be translated to gcode by the controller later
        depending on the controller's functionality.
        Args:
            argkv: A dict containing one or more of the following parameters:
                command: The gcode command as a string. Defaults to "G01".
                x: The x coordinate.
                y: The y coordinate.
                z: The z coordinate.
                f: The feed rate.
        """
        self.publish_one_by_value("command:move_absolute", argkv)

    def g92_offsets(self, **argkv: Union[str, float]) -> None:
        """ Set work position offset.
        http://linuxcnc.org/docs/2.6/html/gcode/coordinates.html#cha:coordinate-system
        """
        argkv["command"] = "G92"

        self._gcode_command("non_modal", **argkv)

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

        gcode = block.Block()
        gcode.gcodes.append(gcode_word(**argkv))
        self.publish_one_by_value("command:gcode", gcode)

