from enum import Enum
from collections import deque

from pygcode import Machine

from definitions import FlagState, Command, Response, State

class ConnectionState(Enum):
    UNKNOWN = 0
    NOT_CONNECTED = 1
    MISSING_RESOURCE = 2
    CONNECTING = 3
    CONNECTED = 4
    DISCONNECTING = 5
    FAIL = 6
    
class _ControllerBase:
    """ Base class for CNC machine control hardware. """

    # Strings of the gcode commands this controller supports.
    SUPPORTED_GCODE = set()

    def __init__(self, label):
        self.label: str = label
        self.active: bool = False
        self.readyForPush: bool = False
        self.readyForPull: bool = False
        self.connectionStatus: ConnectionState = ConnectionState.UNKNOWN
        self.gui: [] = []
        self.state: State = State(vm=Machine())
        self.gcode: deque = deque()
    
    def push(self, data: Command) -> bool:
        assert False, "Undefined method"
        return False

    def pull(self) -> Response:
        assert False, "Undefined method"
        return ""

    def connect(self):
        assert False, "Undefined method"
        return ConnectionState.UNKNOWN

    def disconnect(self):
        assert False, "Undefined method"
        return ConnectionState.UNKNOWN

    def service(self):
        assert False, "Undefined method"
       
    def isGcodeSupported(self, command: str) -> bool:
        return str(command) in self.SUPPORTED_GCODE
