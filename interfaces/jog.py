from interfaces._interfaceBase import _InterfaceBase, UpdateState, InterfaceState
from definitions import FlagState, State

className = "JogWidget"

class JogWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    def __init__(self, label: str = "jogWidget"):
        super().__init__(label)
        self.readyForPush = True
        self.readyForPull = False

    def connect(self):
        self.status = InterfaceState.STALE_DATA
        return self.status

    def disconnect(self):
        self.status = InterfaceState.UNKNOWN
        return self.status

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
        super().moveTo(**argkv)
        self._updatedData.jog = FlagState.TRUE
