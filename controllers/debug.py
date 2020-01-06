from typing import Dict
import time

import PySimpleGUI as sg

from controllers._controllerBase import _ControllerBase
from definitions import Command, Response, ConnectionState

CONNECT_DELAY =  4  # seconds
PUSH_DELAY = 1      # seconds
PULL_DELAY = 1      # seconds

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

    def __init__(self, label: str="debug"):
        super().__init__(label)
        self._connectTime: int = 0;
        self._lastPushAt: int = 0;
        self._lastPullAt: int = 0;
        self._sequences: [] = []

    def guiLayout(self):
        layout = [
                [sg.Text("Title:"), sg.Text("unknown", key=self.keyGen("label"))],
                [sg.Text("Sequence:"), sg.Text(size=(6,1), key="confirmedSequence")],
                [sg.Text("Connection state:"),
                    sg.Text(size=(18,1), key=self.keyGen("connectionStatus"))],
                [sg.Text("Desired:"),
                    sg.Text(size=(18,1), key=self.keyGen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="gcode", size=(200, 10), key=self.keyGen("gcode"),
                              autoscroll=True, disabled=True)],
                [
                    sg.Button('Connect', key=self.keyGen("connect")),
                    sg.Button('Disconnect', key=self.keyGen("disconnect")),
                    sg.Exit()
                    ],
                ]
        return layout
    
    def push(self, data: Command) -> bool:
        assert self.readyForPush, "readyForPush flag not set"
        assert self.connectionStatus == ConnectionState.CONNECTED, \
                "Controller not connected"

        self._lastPushAt = time.time()

        self.state.confirmedSequence = data.sequence
        if data.gcode:
            self._sequences.append(data)
            self.gcode.append(data.gcode)
            print("CONTROLLER: %s  RECEIVED: %s  BUFFER: %s" %
                    (self.label, data.gcode["gcode"].gcodes, len(self.gcode)))
            gcode = ""
            for line in self.gcode:
                gcode += str(line["gcode"].gcodes) + "\n"
            self.publishOneByValue("debug:gcode", gcode)
        self.readyForPush = False
        return True

    def pull(self) -> Response:
        assert self.readyForPull, "readyForPull flag not set"
        assert self.connectionStatus == ConnectionState.CONNECTED, \
                "Controller not connected"

        if time.time() - self._lastPullAt < PULL_DELAY:
            return None
        self._lastPullAt = time.time()

        return Response(self.state.confirmedSequence)

    def connect(self) :
        if self.connectionStatus in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.CONNECTING)
        self._connectTime = time.time()
        return self.connectionStatus

    def disconnect(self) :
        if self.connectionStatus in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.DISCONNECTING)
        self._connectTime = time.time()

        self.readyForPush = False
        self.readyForPull = False
        
        return self.connectionStatus
    
    def service(self):
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
            if time.time() - self._lastPushAt >= PUSH_DELAY:
                self.readyForPush = True
            if time.time() - self._lastPullAt >= PULL_DELAY and self._sequences:
                self.readyForPull = True
        else:
                self.readyForPush = False
                self.readyForPull = False

        self.processDeliveredEvents()

