from typing import Dict, Any, Deque, Set
from enum import Enum
from collections import deque

from pygcode import GCode

from component import _ComponentBase
from definitions import FlagState, ConnectionState, ConnectionStateTypes

class _ControllerBase(_ComponentBase):
    """ Base class for CNC machine control hardware. """

    # Strings of the gcode commands this controller supports.
    SUPPORTED_GCODE: Set = set()

    def __init__(self, label: str) -> None:
        super().__init__(label)

        self.__active: bool = False
        self.readyForData: bool = False
        self.connectionStatus: ConnectionState = ConnectionState.UNKNOWN
        self.desiredConnectionStatus: ConnectionState = ConnectionState.NOT_CONNECTED
        self._newGcodeLine = None
        self._queuedUpdates: Deque = deque()

        # Map incoming events to local member variables and callback methods.
        self.label = label
        self.eventSubscriptions = {
                self.keyGen("connect"):
                ("setDesiredConnectionStatus", ConnectionState.CONNECTED),
                self.keyGen("disconnect"):
                ("setDesiredConnectionStatus", ConnectionState.NOT_CONNECTED),
                "desiredState:newGcode": ("_newGcodeLine", None),
                }

        self.setConnectionStatus(ConnectionState.UNKNOWN)
        self.setDesiredConnectionStatus(ConnectionState.NOT_CONNECTED)

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, value: bool) -> None:
        self.__active = value
        if value:
            self.onActivate()
        else:
            self.onDeactivate()

    def onActivate(self) -> None:
        """ Called whenever self.active is set True. """
        pass

    def onDeactivate(self) -> None:
        """ Called whenever self.active is set False. """
        pass

    def setDesiredConnectionStatus(self, connectionStatus: ConnectionStateTypes) -> None:
        self.desiredConnectionStatus = connectionStatus
        self.publishOneByValue(self.keyGen("desiredConnectionStatus"), connectionStatus)

    def setConnectionStatus(self, connectionStatus: ConnectionStateTypes) -> None:
        self.connectionStatus = connectionStatus
        self.publishOneByValue(self.keyGen("connectionStatus"), connectionStatus)

    def connect(self) -> ConnectionStateTypes:
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def disconnect(self) -> ConnectionStateTypes:
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

    def update(self) -> None:
        if(self._delivered and
                self.connectionStatus is ConnectionState.CONNECTED and
                self.active):
            # Save incoming data to local buffer until it can be processed.
            # (self._delivered will be cleared later this iteration.)
            for event, value in self._delivered:
                if event == "desiredState:newGcode":
                    self._queuedUpdates.append(value)
                # TODO: Flags.



