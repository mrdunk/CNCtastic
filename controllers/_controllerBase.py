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
        self.active: bool = False
        self.readyForPush: bool = False
        self.readyForPull: bool = False
        self.connectionStatus: ConnectionState = ConnectionState.UNKNOWN
        self.desiredConnectionStatus: ConnectionState = ConnectionState.NOT_CONNECTED
        self.state: State = State(vm=Machine())
        self._newGcodeLine = None
        self.gcode: deque = deque()

        # Map incoming events to local member variables and callback methods.
        self.label = label
        self.eventActions = {
                self.keyGen("connect"):
                ("setDesiredConnectionStatus", ConnectionState.CONNECTED),
                self.keyGen("disconnect"):
                ("setDesiredConnectionStatus", ConnectionState.NOT_CONNECTED),
                "desiredState:newGcode": ("_newGcodeLine", None),
                }
        # Need to call super() here as is does config based on self.eventActions.
        super().__init__(label)

        self.setConnectionStatus(ConnectionState.UNKNOWN)
        self.setDesiredConnectionStatus(ConnectionState.NOT_CONNECTED)

    def setDesiredConnectionStatus(self, connectionStatus):
        self.desiredConnectionStatus = connectionStatus
        self.publishOneByValue(self.keyGen("desiredConnectionStatus"), connectionStatus)

    def setConnectionStatus(self, connectionStatus):
        self.connectionStatus = connectionStatus
        self.publishOneByValue(self.keyGen("connectionStatus"), connectionStatus)

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

    def isGcodeSupported(self, command: str) -> bool:
        return str(command) in self.SUPPORTED_GCODE
    
    def service(self):
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        raise NotImplementedError


