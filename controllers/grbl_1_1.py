from typing import Dict
import time
import serial
import threading
from queue import Queue, Empty

import PySimpleGUI as sg

from controllers._controllerBase import _ControllerBase
from definitions import ConnectionState, State, MODAL_COMMANDS


REPORT_INTERVAL = 1.0 # seconds
SERIAL_INTERVAL = 0.02 # seconds


className = "Grbl1p1Controller"

class Grbl1p1Controller(_ControllerBase):

    # GRBL1.1 only supports the following subset of gcode.
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

    GRBL_STATUS_HEADERS = {b"MPos": "machinePos",
                           b"WPos": "workPos",
                           b"FS": "feedRate",    # Variable spindle.
                           b"F": "feedRate",     # Non variable spindle.
                           b"Pn": "inputPins",
                           b"WCO": "workCoordOffset",
                           b"Ov": "overrideValues",
                           b"Bf": "bufferState",
                           b"Ln": "lineNumber",
                           b"A": "accessoryState"
                           } 
    MACHINE_STATES = [
            b"Idle", b"Run", b"Hold", b"Jog", b"Alarm", b"Door", b"Check", b"Home", b"Sleep"]

    MODALS = MODAL_COMMANDS

    def __init__(self, label: str="grbl1.1"):
        super().__init__(label)
        self.state = State()
        #self.serialDevName = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        self.serialDevName = "/tmp/ttyFAKE"
        self.serialBaud = 115200
        self._serial = None
        self._lastWrite = 0
        self._partialRead: str = b""
        self._commandImmediate = Queue()
        self._commandStreaming = Queue()
    
    def guiLayout(self):
        layout = [
                [sg.Text("Title:", size=(20,1)),
                    sg.Text("unknown", key=self.keyGen("label"), size=(20,1))],
                [sg.Text("Connection state:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("connectionStatus"))],
                [sg.Text("Desired:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="Machine state", size=(200, 10),
                              key=self.keyGen("state"),
                              autoscroll=True, disabled=True)],
                [
                    sg.Button('Connect', key=self.keyGen("connect"), size=(10, 1), pad=(2, 2)),
                    sg.Button('Disconnect', key=self.keyGen("disconnect"),
                              size=(10, 1), pad=(2, 2)),
                    sg.Exit(size=(10, 1), pad=(2, 2))
                    ],
                ]
        return layout
    
    def connect(self):
        print("connect")
        if self.connectionStatus in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.CONNECTING)
        
        try:
            self._serial = serial.serial_for_url(
                    self.serialDevName, self.serialBaud, timeout=0)
        except AttributeError:
            try:
                self._serial = serial.Serial(
                        self.serialDevName, self.serialBaud, timeout=0)
            except serial.serialutil.SerialException:
                self.setConnectionStatus(ConnectionState.MISSING_RESOURCE)
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.MISSING_RESOURCE)
            

        return self.connectionStatus

    def disconnect(self) :
        print("disconnect")
        if self.connectionStatus in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connectionStatus

        if self._serial is None:
            self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        else:
            self.setConnectionStatus(ConnectionState.DISCONNECTING)

            self._serialThread.join()
            self._serial.close()

        self.readyForData = False
        
        return self.connectionStatus

    def onConnected(self):
        if not self._serial.is_open:
            return

        print("Serial connected.")
        self.setConnectionStatus(ConnectionState.CONNECTED)

        #self._serial.write(b"$G\n")
        self._commandImmediate.put(b"$G\n")

        self._serialThread = threading.Thread(target=self._periodicIO)
        self._serialThread.daemon = True
        self._serialThread.start()

        print("done")

    def onDisconnected(self):
        if self._serial.is_open:
            return

        print("Serial disconnected.")
        self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        self._serial = None

    def _write(self, string):
        try:
            self._serial.write(string)
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.FAIL)

    def _parseCoordinates(self, string) -> Dict:
        parts = string.split(b",")
        assert len(parts) >= 3
        coordinates = {}
        coordinates["x"] = float(parts[0])
        coordinates["y"] = float(parts[1])
        coordinates["z"] = float(parts[2])
        if len(coordinates) > 3:
            coordinates["a"] = float(parts[3])
        return coordinates

    def _setCoordinates(self, identifier, value):
        if identifier == b"MPos":
            self.state.setMachinePos(self._parseCoordinates(value))
        elif identifier == b"WPos":
            self.state.setWorkPos(self._parseCoordinates(value))
        elif identifier == b"WCO":
            self.state.setWorkOffset(self._parseCoordinates(value))
        else:
            print("Invalid format: %s  Expected one of [MPos, WPos]" % posId)

    def _setOverrides(self, value):
        feedOverrride, rapidOverrride, spindleOverride = value.split(b",")
        feedOverrride = int(float(feedOverrride))
        rapidOverrride = int(float(rapidOverrride))
        spindleOverride = int(float(spindleOverride))
        
        if 10 <= feedOverrride <= 200:
            self.state.feedOverrride = feedOverrride
        if rapidOverrride in [100, 50, 20]:
            self.state.rapidOverrride = rapidOverrride
        if 10 <= spindleOverride <= 200:
            self.state.spindleOverride = spindleOverride

    def _setFeedSpindle(self, value):
        feed, spindle = value.split(b",")
        self.state.feedRate = int(float(feed))
        self.state.spindleRate = int(float(spindle))

    def _setFeed(self, value):
        self.state.spindleRate = int(float(value))

    def _setState(self, state):
        states = state.split(b":")
        assert len(states) <=2, "Invalid state: %s" % state

        if len(states) == 1:
            substate = None
        else:
            state, substate = states
            
        assert state in self.MACHINE_STATES
        if state in [b"Idle", b"Run", b"Jog", b"Home"]:
            self.state.pause = False
            self.state.pausePark = False
            self.state.halt = False
            self.state.door = False
            self.state.resetComplete = False
            self.state.pauseReason.clear()
            self.state.haltReason.clear()
            self.state.resetReason.clear()
        elif state == b"Hold":
            pass
        elif state == b"Alarm":
            pass
        elif state == b"Door":
            pass
        elif state == b"Check":
            pass
        elif state == b"Sleep":
            pass

    def _parseIncomingStatus(self, incoming):
        assert incoming.startswith(b"<") and incoming.endswith(b">")

        incoming = incoming.strip(b"<>")

        fields = incoming.split(b"|")
        
        machineState = fields[0]
        self._setState(machineState)

        for field in fields[1:]:
            identifier, value = field.split(b":")
            assert identifier in self.GRBL_STATUS_HEADERS
            if identifier in [b"MPos", b"WPos", b"WCO"]:
                self._setCoordinates(identifier, value)
            elif identifier == b"Ov":
                self._setOverrides(value)
            elif identifier == b"FS":
                self._setFeedSpindle(value)
            elif identifier == b"F":
                self._setFeed(value)
            else:
                print(identifier, value)

        self.state.eventFired = False
    
    def _parseIncomingFeedbackModal(self, msg):
        """ In response to a "$G" command, GRBL sends a G-code Parser State Message
        in the format:
        [GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0.0 S0]
        Each word is in a different modal group.
        self.MODALS maps these words to a group. eg: G0 is in the "motion" group.  """
        modals = msg.split(b" ")
        for modal in modals:
            if modal in self.MODALS:
                modalGroup = self.MODALS[modal]
                self.state.gcodeModal[modalGroup] = modal
            elif chr(modal[0]).encode('utf-8') in self.MODALS:
                modalGroup = self.MODALS[chr(modal[0]).encode('utf-8')]
                self.state.gcodeModal[modalGroup] = modal
            else:
                print(modal, chr(modal[0]).encode('utf-8'))
                assert False, "Gcode word does not match any mmodal group: %s" % modal

    def _parseIncomingFeedback(self, incoming):
        assert incoming.startswith(b"[") and incoming.endswith(b"]")

        incoming = incoming.strip(b"[]")

        msgType, msg = incoming.split(b":")

        if msgType == b"MSG":
            print(incoming)
        elif msgType == b"GC":
            self._parseIncomingFeedbackModal(msg)

    def _parseIncomingOk(self, incoming):
        print("OK:", incoming)

    def _parseIncomingAlarm(self, incoming):
        print("ALARM:", incoming)

    def _parseError(self, incoming):
        print("ERROR:", incoming)

    def _parseSetting(self, incoming):
        print("Setting:", incoming)

    def _parseStartupLine(self, incoming):
        print("Startup:", incoming)
        assert incoming.startswith(b">") and incomming.endswith(b":ok")
        print("Startup successful.")

    def _parseStartup(self, incoming):
        print("GRBL Startup:", incoming)

    def _parseIncoming(self, incoming):
        if self._partialRead:
            incoming = self._partialRead + incoming
        
        if not incoming.endswith(b"\r\n"):
            pos = incoming.find(b"\r\n")
            if pos > 0:
                tmpIncoming = self._partialRead + incoming[:pos + 2]
                self._partialRead = incoming[pos + 2:]
                incoming = tmpIncoming
            else:
                self._partialRead += incoming
                return

        incoming = incoming.strip()

        if incoming.startswith(b"error:"):
            self._parseError(incoming)
        elif incoming.startswith(b"ALARM:"):
            self._parseIncomingAlarm(incoming)
        elif incoming.startswith(b"ok"):
            self._parseIncomingOk(incoming)
        elif incoming.startswith(b"<"):
            self._parseIncomingStatus(incoming)
        elif incoming.startswith(b"["):
            self._parseIncomingFeedback(incoming)
        elif incoming.startswith(b"$"):
            self._parseSetting(incoming)
        elif incoming.startswith(b">"):
            self._parseStartup(incoming)
        elif incoming.startswith(b"Grbl "):
            self._parseStartup(incoming)
        else:
            print(incoming)

    def _periodicIO(self):
        while self.connectionStatus is ConnectionState.CONNECTED:
            # Read
            try:
                line = self._serial.readline()
            except serial.serialutil.SerialException:
                self.setConnectionStatus(ConnectionState.FAIL)
            if line:
                self._parseIncoming(line)

            #Write
            task = None
            try:
                task = self._commandImmediate.get(block=False)
            except Empty:
                try:
                    task = self._commandStreaming.get(block=False)
                except Empty:
                    pass
            if task is not None:
                self._write(task)

            if self._lastWrite < time.time() - REPORT_INTERVAL:
                self._write(b"?")
                self._lastWrite = time.time()
            time.sleep(SERIAL_INTERVAL)


    def service(self):
        if self.connectionStatus != self.desiredConnectionStatus:
            if self.connectionStatus is ConnectionState.CONNECTING:
                self.onConnected()

            elif self.connectionStatus is ConnectionState.DISCONNECTING:
                self.onDisconnected()

            elif self.connectionStatus in [
                    ConnectionState.FAIL, ConnectionState.MISSING_RESOURCE]:
                print("self.connectionStatus is ConnectionState.FAIL")
                self.setDesiredConnectionStatus(ConnectionState.NOT_CONNECTED)
                self.setConnectionStatus(ConnectionState.CLEANUP)

            elif self.desiredConnectionStatus is ConnectionState.CONNECTED:
                self.connect()

            elif self.desiredConnectionStatus is ConnectionState.NOT_CONNECTED:
                self.disconnect()
        
        if self.connectionStatus is ConnectionState.CONNECTED:
            if not self.state.eventFired:
                self.publishOneByValue(self.keyGen("state"), self.state)
                self.state.eventFired = True

    def processDeliveredEvents(self):
        super().processDeliveredEvents()

        if self._queuedGcode:
            # Process local buffer.
            pass

