from typing import Dict, List, Any
try:
    from typing import Literal              # type: ignore
except:
    from typing_extensions import Literal   # type: ignore

from controllers.debug import DebugController
from definitions import ConnectionState

class MockController(DebugController):
    def __init__(self, label: str="debug") -> None:
        super().__init__(label)
        self.logCallData: Dict = {}
        self.overideCallReturn: Dict = {}

    def logCall(self, method: str, args: List[Any], kvargs: Dict[str, Any]) -> None:
        if method not in self.logCallData:
            self.logCallData[method] = []
        self.logCallData[method].append((args, kvargs))

    def overideReturn(self, method: str, expectedReturnVal: Any) -> Literal[ConnectionState]:
        if method in self.overideCallReturn:
            if isinstance(self.overideCallReturn[method], list):
                self.overideCallReturn[method].pop()
            else:
                return self.overideCallReturn[method]
        return expectedReturnVal

    def earlyUpdate(self) -> None:
        if self.connectionStatus == ConnectionState.CONNECTING:
            self.connectionStatus = ConnectionState.CONNECTED
        elif self.connectionStatus == ConnectionState.DISCONNECTING:
            self.connectionStatus = ConnectionState.NOT_CONNECTED

        if self.connectionStatus == ConnectionState.CONNECTED:
            self.readyForData = True
        else:
            self.readyForData = False

