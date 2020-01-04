from controllers.debug import DebugController
from definitions import Command, Response, ConnectionState

class MockController(DebugController):
    def __init__(self, label="debug"):
        super().__init__(label)
        self.logCallData: {} = {}
        self.overideCallReturn: {} = {}

    def logCall(self, method, args, kvargs):
        if method not in self.logCallData:
            self.logCallData[method] = []
        self.logCallData[method].append((args, kvargs))

    def overideReturn(self, method, expectedReturnVal):
        if method in self.overideCallReturn:
            if isinstance(self.overideCallReturn[method], list):
                self.overideCallReturn[method].pop()
            else:
                return self.overideCallReturn[method]
        return expectedReturnVal

    def push(self, data: Command) -> bool:
        self.logCall("push", [data], {})
        
        self._sequences.append(data)
        self.readyForPush = False

        return self.overideReturn("push", True)

    def pull(self) -> Response:
        self.logCall("pull", [], {})
        returnVal = Response(self.state.confirmedSequence)
        return self.overideReturn("pull", returnVal)
    
    def service(self):
        if self.connectionStatus == ConnectionState.CONNECTING:
            self.connectionStatus = ConnectionState.CONNECTED
        elif self.connectionStatus == ConnectionState.DISCONNECTING:
            self.connectionStatus = ConnectionState.NOT_CONNECTED

        if not self.connectionStatus == ConnectionState.CONNECTED:
            self.readyForPush = False
            self.readyForPull = False

