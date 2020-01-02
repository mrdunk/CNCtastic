import time

from controllers._controllerBase import ConnectionState, _ControllerBase
from definitions import Command, Response

CONNECT_DELAY = 10  # seconds
PUSH_DELAY = 1      # seconds
PULL_DELAY = 1      # seconds

className = "DebugController"

class DebugController(_ControllerBase):

    # Mimic GRBL compatibility here. https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands
    SUPPORTED_GCODE = set((
            "G00", "G01", "G02", "G03", "G38.2", "G38.3", "G38.4", "G38.5", "G80",
            "G54", "G55", "G56", "G57", "G58", "G59",
            "G17", "G18", "G19",
            "G90", "G91",
            "G91.1",
            "G93", "G94",
            "G20", "G21",
            "G40",
            "G43.1", "G49",
            "M00", "M01", "M02", "M30",
            "M03", "M04", "M05",
            "M07", "M08", "M09",
            "G04", "G10 L2", "G10 L20", "G28", "G30", "G28.1", "G30.1", "G53", "G92", "G92.1",
            ))

    def __init__(self, label: str="debug"):
        super().__init__(label)
        self._connectTime: int = 0;
        self._lastPushAt: int = 0;
        self._lastPullAt: int = 0;
        self._sequences: [] = []

    def push(self, data: Command) -> bool:
        assert self.readyForPush, "readyForPush flag not set"
        assert self.connectionStatus == ConnectionState.CONNECTED, \
                "Controller not connected"
        
        if time.time() - self._lastPushAt < PUSH_DELAY:
            return False
        self._lastPushAt = time.time()

        self._sequences.append(data)
        self.state.latestSequence = data.sequence
        self.gcode.append(data.gcode)
        self.readyForPush = False
        return True

    def pull(self) -> Response:
        assert self.readyForPull, "readyForPull flag not set"
        assert self.connectionStatus == ConnectionState.CONNECTED, \
                "Controller not connected"

        if time.time() - self._lastPullAt < PULL_DELAY:
            return None
        self._lastPullAt = time.time()

        return Response(self.state.latestSequence)

    def connect(self) :
        if(not self.connectionStatus == ConnectionState.NOT_CONNECTED and
                not self.connectionStatus == ConnectionState.UNKNOWN):
            return self.connectionStatus

        self.connectionStatus = ConnectionState.CONNECTING
        self._connectTime = time.time()
        return self.connectionStatus

    def disconnect(self) :
        if(not self.connectionStatus == ConnectionState.CONNECTED and
                not self.connectionStatus == ConnectionState.UNKNOWN):
            return self.connectionStatus

        self.connectionStatus = ConnectionState.DISCONNECTING
        self._connectTime = time.time()

        self.readyForPush = False
        self.readyForPull = False
        
        return self.connectionStatus
    
    def service(self):
        if time.time() - self._connectTime >= CONNECT_DELAY:
            if self.connectionStatus == ConnectionState.CONNECTING:
                self.connectionStatus = ConnectionState.CONNECTED
            elif self.connectionStatus == ConnectionState.DISCONNECTING:
                self.connectionStatus = ConnectionState.NOT_CONNECTED

        if time.time() - self._lastPushAt >= PUSH_DELAY:
            self.readyForPush = True
        if time.time() - self._lastPullAt >= PULL_DELAY and self._sequences:
            self.readyForPull = True


