import time
import serial
import serial.threaded
import threading

import PySimpleGUI as sg

from controllers._controllerBase import _ControllerBase
from definitions import ConnectionState


REPORT_INTERVAL = 1.0 # seconds


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

    def __init__(self, label: str="grbl1.1"):
        super().__init__(label)
        self.serialDevName = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        #self.serialDevName = "/tmp/ttyFAKE"
        self.serialBaud = 115200
        self._serial = None
    
    def guiLayout(self):
        layout = [
                [sg.Text("Title:", size=(20,1)),
                    sg.Text("unknown", key=self.keyGen("label"), size=(20,1))],
                [sg.Text("Connection state:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("connectionStatus"))],
                [sg.Text("Desired:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="gcode", size=(200, 10), key=self.keyGen("gcode"),
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
        #print("connect")
        if self.connectionStatus in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.CONNECTING)
        try:
            self._serial = serial.serial_for_url(self.serialDevName, self.serialBaud, timeout=0)
        except AttributeError:
            print("except AttributeError")
            self._serial = serial.Serial(self.serialDevName, self.serialBaud, timeout=0)


        return self.connectionStatus

    def disconnect(self) :
        #print("disconnect")
        if self.connectionStatus in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connectionStatus

        if self._serial is None:
            self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        else:
            self.setConnectionStatus(ConnectionState.DISCONNECTING)
            self._serial.close()

        self.readyForData = False
        
        return self.connectionStatus

    def onConnected(self):
        if not self._serial.is_open:
            return

        print("Serial connected.")
        self.setConnectionStatus(ConnectionState.CONNECTED)

        #self._serial.write(b"?")
        #time.sleep(2)
        #print(self._serial.readline())

        timerThread = threading.Thread(target=self.periodicRead)
        timerThread.daemon = True
        timerThread.start()

    def onDisconnected(self):
        if self._serial.is_open:
            return

        print("Serial disconnected.")
        self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        self._serial = None

    def periodicRead(self):
        while self.connectionStatus is ConnectionState.CONNECTED:
            print(self._serial.readline())
            self._serial.write(b"?")
            time.sleep(REPORT_INTERVAL)


    def service(self):
        if self.connectionStatus != self.desiredConnectionStatus:
            if self.connectionStatus is ConnectionState.CONNECTING:
                self.onConnected()

            elif self.connectionStatus is ConnectionState.DISCONNECTING:
                self.onDisconnected()

            elif self.desiredConnectionStatus is ConnectionState.CONNECTED:
                self.connect()

            elif self.desiredConnectionStatus is ConnectionState.NOT_CONNECTED:
                self.disconnect()


    def processDeliveredEvents(self):
        super().processDeliveredEvents()

        if self._queuedGcode:
            # Process local buffer.
            pass

