from interfaces.jog import JogWidget

class MockWidget(JogWidget):
    def __init__(self):
        super().__init__("MockWidget")
        
        self.logCallData: {} = {}
        self.overideCallReturn: {} = {}

        self._getInputRun = False

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

