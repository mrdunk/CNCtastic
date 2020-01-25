from typing import Dict, Deque, List
try:
    from typing import Literal              # type: ignore
except:
    from typing_extensions import Literal   # type: ignore
import time
from collections import deque

#import PySimpleGUIQt as sg
from terminals.gui import sg

from controllers._controllerBase import _ControllerBase
from definitions import ConnectionState

CONNECT_DELAY =  4  # seconds
PUSH_DELAY = 1      # seconds

className = "DebugController"

class DebugController(_ControllerBase):

    # Mimic GRBL compatibility in this controller.
    # https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands
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

    def __init__(self, label: str="debug") -> None:
        super().__init__(label)
        self.gcode: deque = deque()
        self._connectTime: float = 0;
        self._lastReceiveDataAt: float = 0;

    def guiLayout(self) -> List:
        layout = [
                [sg.Text("Title:", size=(20,1)),
                    sg.Text(self.label, key=self.keyGen("label"), size=(20,1)),
                    sg.Checkbox("Active", default=self.active, key=self.keyGen("active"))],
                [sg.Text("Connection state:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("connectionStatus"))],
                [sg.Text("Desired:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="gcode", size=(60, 10), key=self.keyGen("gcode"),
                              autoscroll=True, disabled=True)],
                [
                    sg.Button('Connect', key=self.keyGen("connect"), size=(10, 1),
                              pad=(2, 2)),
                    sg.Button('Disconnect', key=self.keyGen("disconnect"),
                              size=(10, 1), pad=(2, 2)),
                    sg.Exit(size=(10, 1), pad=(2, 2))
                    ],
                ]
        return layout
    
    def connect(self) -> Literal[ConnectionState]:
        if self.connectionStatus in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.CONNECTING)
        self._connectTime = time.time()
        return self.connectionStatus

    def disconnect(self) -> Literal[ConnectionState]:
        if self.connectionStatus in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.DISCONNECTING)
        self._connectTime = time.time()

        self.readyForData = False
        
        return self.connectionStatus
    
    def earlyUpdate(self) -> None:
        if self.connectionStatus != self.desiredConnectionStatus:
            if time.time() - self._connectTime >= CONNECT_DELAY:
                if self.connectionStatus == ConnectionState.CONNECTING:
                    self.setConnectionStatus(ConnectionState.CONNECTED)
                elif self.connectionStatus == ConnectionState.DISCONNECTING:
                    self.setConnectionStatus(ConnectionState.NOT_CONNECTED)

            if self.desiredConnectionStatus == ConnectionState.CONNECTED:
                self.connect()
            elif self.desiredConnectionStatus == ConnectionState.NOT_CONNECTED:
                self.disconnect()

        if self.connectionStatus == ConnectionState.CONNECTED:
            if time.time() - self._lastReceiveDataAt >= PUSH_DELAY:
                self.readyForData = True
        else:
                self.readyForData = False
    
    def update(self) -> None:
        super().update()

        if self.readyForData and self._queuedUpdates:
            # Process local buffer.
            self._lastReceiveDataAt = time.time()
            update = self._queuedUpdates.popleft()
            jog = update.jog.name
            gcode = update.gcode

            self.gcode.append((jog, gcode))
            if self.debugShowEvents:
                print("CONTROLLER: %s  RECEIVED: %s  BUFFER: %s" %
                        (self.label, gcode.gcodes, len(self.gcode)))
        
            gcodeDebugOutput = ""
            for jog, gc in self.gcode:
                gcodeDebugOutput += "%s ; jog=%s ; supported=%s\n" % (
                        str(gc.gcodes), jog, self.isGcodeSupported(gc.gcodes))
            self.publishOneByValue(self.keyGen("gcode"), gcodeDebugOutput)

