from typing import Any, Dict, List

from interfaces.jog import JogWidget  # type: ignore

class MockWidget(JogWidget):
    def __init__(self) -> None:
        super().__init__("MockWidget")
        
        self.logCallData: Dict = {}
        self.overideCallReturn: Dict = {}

        self._getInputRun = False

    def logCall(self, method: str, args: List[Any], kvargs: Dict[str, Any]) -> None:
        if method not in self.logCallData:
            self.logCallData[method] = []
        self.logCallData[method].append((args, kvargs))

    def overideReturn(self, method: str, expectedReturnVal: Any) -> Any:
        if method in self.overideCallReturn:
            if isinstance(self.overideCallReturn[method], list):
                self.overideCallReturn[method].pop()
            else:
                return self.overideCallReturn[method]
        return expectedReturnVal

