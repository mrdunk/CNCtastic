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

    def service(self):
        if self.connectionStatus == ConnectionState.CONNECTING:
            self.connectionStatus = ConnectionState.CONNECTED
        elif self.connectionStatus == ConnectionState.DISCONNECTING:
            self.connectionStatus = ConnectionState.NOT_CONNECTED

        if self.connectionStatus == ConnectionState.CONNECTED:
            self.readyForPush = True
        else:
            self.readyForPush = False

