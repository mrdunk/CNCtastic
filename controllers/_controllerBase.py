from typing import Dict
from enum import Enum
from collections import deque

from pygcode import Machine

from coordinator.coordinator import _CoreComponent
from definitions import FlagState, Command, Response, State, ConnectionState

class _ControllerBase(_CoreComponent):
    """ Base class for CNC machine control hardware. """

    # Strings of the gcode commands this controller supports.
    SUPPORTED_GCODE = set()

    def __init__(self, label):
        self.label: str = label
        self.active: bool = False
        self.readyForPush: bool = False
        self.readyForPull: bool = False
        self.connectionStatus: ConnectionState = ConnectionState.UNKNOWN
        self.desiredConnectionStatus: ConnectionState = ConnectionState.NOT_CONNECTED
        self.state: State = State(vm=Machine())
        self.gcode: deque = deque()

        self.eventActions = {
                "%s:connect" % self.label:
                ("desiredConnectionStatus", ConnectionState.CONNECTED),
                "%s:disconnect" % self.label:
                ("desiredConnectionStatus", ConnectionState.NOT_CONNECTED),
                }

    def push(self, data: Command) -> bool:
        raise NotImplementedError
        return False

    def pull(self) -> Response:
        raise NotImplementedError
        return ""

    def connect(self):
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def disconnect(self):
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def service(self):
        raise NotImplementedError
       
    def isGcodeSupported(self, command: str) -> bool:
        return str(command) in self.SUPPORTED_GCODE

    def exportToGui(self) -> Dict:
        """ Export values in this class to be consumed by GUI.
        Returns:
            A Dict where the key is the key of the GUI widget to be populated
            and the value is a member od this class. """
        return {
                "%s:label" % self.label: self.label,
                "%s:connectionStatus" % self.label: self.connectionStatus,
                "%s:desiredConnectionStatus" % self.label: self.desiredConnectionStatus,
                }

