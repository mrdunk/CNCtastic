""" Plugin providing interface to control of some aspect of the active controller. """

from typing import Union

from pygcode import block, GCodeCoordSystemOffset

from interfaces._interface_base import _InterfaceBase


class _InterfaceMovementBase(_InterfaceBase):
    """ A base class for user input objects used for controlling movement aspects
    of the machine. """

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
        gcode = block.Block()
        gcode.gcodes.append(GCodeCoordSystemOffset(**argkv))
        self.publish_one_by_value("command:gcode", gcode)
