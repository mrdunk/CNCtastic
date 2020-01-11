from typing import Dict, Any
from enum import Enum
from collections import deque

from pygcode import Machine

from component import _ComponentBase
from definitions import FlagState, Command, State, ConnectionState

class _ControllerBase(_ComponentBase):
    """ Base class for CNC machine control hardware. """

    # Strings of the gcode commands this controller supports.
    SUPPORTED_GCODE = set()

    def __init__(self, label):
        self.active: bool = False
        self.readyForData: bool = False
        self.connectionStatus: ConnectionState = ConnectionState.UNKNOWN
        self.desiredConnectionStatus: ConnectionState = ConnectionState.NOT_CONNECTED
        self.state: State = State(vm=Machine())
        self._newGcodeLine = None
        self._queuedGcode: Deque = deque()

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

    def connect(self):
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def disconnect(self):
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def isGcodeSupported(self, command: Any) -> bool:
        if isinstance(command, list):
            returnVal = True
            for gcode in command:
                returnVal = returnVal and str(gcode.word_key) in self.SUPPORTED_GCODE
            return returnVal
        elif isinstance(command, GCode):
            return str(command.word_key) in self.SUPPORTED_GCODE
        elif isinstance(command, str):
            return str(command) in self.SUPPORTED_GCODE
        
        raise AttributeError("Cannot tell if %s is valid gcode." % command)

    def processDeliveredEvents(self):
        if(self._delivered and
                self.connectionStatus is ConnectionState.CONNECTED and
                self.active):
            # Save incoming data to local buffer until it can be processed.
            # (self._delivered will be cleared later this iteration.)
            for event, value in self._delivered:
                if event == "desiredState:newGcode":
                    self._queuedGcode.append(value)
                # TODO: Flags.



