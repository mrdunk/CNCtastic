from interfaces.jog import JogWidget
from interfaces._interfaceBase import UpdateState
from definitions import State

class MockWidget(JogWidget):
    def __init__(self):
        super().__init__("MockWidget")
        
        # Not the default in the base class but check it here to verify tests.
        self.readyForPush = False

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

    def push(self, data: State) -> bool:
        assert(True == self.readyForPush)

        self.logCall("push", [data], {})
        returnVal = super().push(data)
        return self.overideReturn("push", returnVal)

    def pull(self) -> UpdateState:
        assert(True == self.readyForPull)

        self.logCall("pull", [], {})
        returnVal = super().pull()
        return self.overideReturn("pull", returnVal)
