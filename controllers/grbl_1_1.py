from typing import Dict
import time
import serial
import threading
from queue import Queue, Empty
from collections import deque

#import PySimpleGUIQt as sg
from terminals.gui import sg
from pygcode import GCode, Block

from controllers._controllerBase import _ControllerBase
from interfaces._interfaceBase import UpdateState
from definitions import ConnectionState
from controllers.stateMachine import StateMachineGrbl as State
from definitions import FlagState

REPORT_INTERVAL = 1.0 # seconds
SERIAL_INTERVAL = 0.02 # seconds
RX_BUFFER_SIZE = 128

className = "Grbl1p1Controller"

class Grbl1p1Controller(_ControllerBase):

    # GRBL1.1 only supports the following subset of gcode.
    # https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands
    SUPPORTED_GCODE = set((
            b"G00", b"G01", b"G02", b"G03", b"G38.2", b"G38.3", b"G38.4", b"G38.5", b"G80",
            b"G54", b"G55", b"G56", b"G57", b"G58", b"G59",
            b"G17", b"G18", b"G19",
            b"G90", b"G91",
            b"G91.1",
            b"G93", b"G94",
            b"G20", b"G21",
            b"G40",
            b"G43.1", b"G49",
            b"M00", b"M01", b"M02", b"M30",
            b"M03", b"M04", b"M05",
            b"M07", b"M08", b"M09",
            b"G04", b"G10 L2", b"G10 L20", b"G28", b"G30", b"G28.1", b"G30.1",
            b"G53", b"G92", b"G92.1",
            b"F", b"T", b"S"
            ))

    SUPPORTED_JOG_GCODE = set((
        b"G20", b"G21",  # Inch and millimeter mode
        b"G90", b"G91",  # Absolute and incremental distances
        b"G53",          # Move in machine coordinates
        b"F"
        ))


    def __init__(self, label: str="grbl1.1"):
        super().__init__(label)
        self._time = time  # Allow replacing with a mock version when testing.
        self.state = State(self.publishFromHere)
        #self.serialDevName = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        self.serialDevName = "/tmp/ttyFAKE"
        self.serialBaud = 115200
        self._serial = None
        self._lastWrite = 0
        self._commandImmediate = Queue()
        self._commandStreaming = Queue()
        self._receivedData = Queue()
        self._partialRead: str = b""
        self._errorCount: int = 0
        self._okCount: int = 0
        self._sendBufLens: deque = deque()
        self._sendBufActns: deque = deque()
        self.testing: bool = False

        #self.active: bool = True
    
    def publishFromHere(self, variableName, variableValue):
        self.publishOneByValue(self.keyGen(variableName), variableValue)
        
    def guiLayout(self):
        layout = [
                [sg.Text("Title:", size=(20,1)),
                    sg.Text("unknown", key=self.keyGen("label"), size=(20,1)),
                    sg.Checkbox("Active", default=self.active, key=self.keyGen("active"))],
                [sg.Text("Connection state:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("connectionStatus"))],
                [sg.Text("Desired:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.keyGen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="Machine state", size=(60, 10),
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
        print("Disconnected %s %s" % (self.label, self.serialDevName))
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

        print("Connected %s %s" % (self.label, self.serialDevName))
        self.setConnectionStatus(ConnectionState.CONNECTED)

        # Drain the buffer of any noise.
        self._serial.flush()
        #while self._serial.inWaiting():
        #    print(self._serial.readline())
        while self._serial.readline():
            pass

        #self._serial.write(b"$G\n")
        self._commandStreaming.put(b"$G")

        self._serialThread = threading.Thread(target=self._periodicIO)
        self._serialThread.daemon = True
        self._serialThread.start()

    def onDisconnected(self):
        if self._serial.is_open:
            return

        print("Serial disconnected.")
        self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        self._serial = None

    def _completeBeforeContinue(self, command) -> bool:
        slowCommands = [b"G10 L2 ", b"G10 L20 ", b"G28.1 ", b"G30.1 ", b"$x=", b"$I=",
                        b"$Nx=", b"$RST=", b"G54 ", b"G55 ", b"G56 ", b"G57 ", b"G58 ",
                        b"G59 ", b"G28 ", b"G30 ", b"$$", b"$I", b"$N", b"$#"]
        for slowCommand in slowCommands:
            if slowCommand in command:
                return True
        return False

    def parseIncoming(self, incoming):
        if incoming is None:
            incoming = b""
        if self._partialRead:
            incoming = self._partialRead + incoming

        if not incoming:
            return

        pos = incoming.find(b"\r\n")
        if pos < 0:
            self._partialRead = incoming
            return

        tmpIncoming = incoming[:pos + 2]
        self._partialRead = incoming[pos + 2:]
        incoming = tmpIncoming

        incoming = incoming.strip()
        if not incoming:
            return

        # Handle time critical responses here. Otherwise defer to main thread.
        if incoming.startswith(b"error:"):
            self._incomingError(incoming)
            self._receivedData.put(incoming)
        elif incoming.startswith(b"ok"):
            self._incomingOk(incoming)
        else:
            self._receivedData.put(incoming)

    def _incomingError(self, incoming):
        self._errorCount += 1
        self._sendBufLens.popleft()
        action = self._sendBufActns.popleft()
        print("error: '%s' due to '%s' " % (incoming, action[0]))
        # Feed Hold:
        self._commandImmediate.put(b"!")

    def _incomingOk(self, incoming):
        if not self._sendBufLens:
            return
        self._okCount += 1
        self._sendBufLens.popleft()
        action = self._sendBufActns.popleft()
        print("'ok' acknowledges: %s" % action[0], type(action[1]))
        if isinstance(action[1], GCode):
            self._receivedData.put(b"[sentGcode:%s]" % str(action.modal_copy()).encode("utf-8"))

    def _write(self, task) -> bool:
        try:
            self._serial.write(task)
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.FAIL)
            return False
        return True

    def _writeImmediate(self) -> bool:
        task = None
        try:
            task = self._commandImmediate.get(block=False)
        except Empty:
            return False

        print("_writeImmediate", task)
        return self._write(task)

    def _writeStreaming(self) -> bool:
        if sum(self._sendBufLens) >= RX_BUFFER_SIZE - 1:
            return False

        task = None
        try:
            task = self._commandStreaming.get(block=False)
        except Empty:
            return False

        taskString = task
        if isinstance(task, Block):
            taskString = str(task).encode("utf-8")

        print("_writeStreaming", taskString)
        if self._write(taskString + b"\n"):
            self._sendBufLens.append(len(taskString) + 1)
            self._sendBufActns.append((taskString, task))
            return True
        return False

    def _periodicIO(self):
        """ Read from and write to serial port.
            Called from a separate thread.
            Blocks while serial port remains connected. """
        while self.connectionStatus is ConnectionState.CONNECTED:
            # Read
            while self._serial.inWaiting() or (b"\r\n" in self._partialRead):
                try:
                    line = self._serial.readline()
                except serial.serialutil.SerialException:
                    self.setConnectionStatus(ConnectionState.FAIL)
                self.parseIncoming(line)

            #Write
            if not self._writeImmediate():
                self._writeStreaming()

            # Request status update periodically.
            if self._lastWrite < self._time.time() - REPORT_INTERVAL:
                self._commandImmediate.put(b"?")
                self._lastWrite = self._time.time()

                print("GRBL receive buffer contains %s commands, %s bytes" %
                        (len(self._sendBufLens), sum(self._sendBufLens)))
            self._time.sleep(SERIAL_INTERVAL)

            if self.testing:
                break

    def doCommand(self, command: UpdateState):
        """ Turn the update into something GRBL can parse and put in a command buffer. """
        assert isinstance(command, UpdateState)
        print(command)

        # Flags.
        if command.pause is FlagState.TRUE and self.state.pause == False:
            # GRBL feed hold.
            self._commandImmediate.put(b"!")
        elif command.pause is FlagState.FALSE and self.state.pause == True:
            if self.state.parking == False:
                # GRBL Cycle Start / Resume
                self._commandImmediate.put(b"~")

        if command.door is FlagState.TRUE and self.state.door == False:
            # GRBL Safety Door.
            self._commandImmediate.put(0x84)
        elif command.door is FlagState.FALSE and self.state.door == True:
            if self.state.parking == False:
                # GRBL Cycle Start / Resume
                self._commandImmediate.put(b"~")

        if command.gcode is not None:
            if command.jog is FlagState.TRUE:
                validGcode = True
                jogCommandString = b"$J="
                for gcode in sorted(command.gcode.gcodes):
                    modal = str(gcode.modal_copy()).encode("utf-8")
                    modalFirst = bytes([modal[0]])
                    if (modal in self.SUPPORTED_JOG_GCODE or
                            modalFirst in self.SUPPORTED_JOG_GCODE):
                        jogCommandString += str(gcode).encode("utf-8")
                    elif modal in [b"G00", b"G0", b"G01", b"G1"]:
                        for param, value in gcode.get_param_dict().items():
                            jogCommandString += param.encode("utf-8")
                            jogCommandString += str(value).encode("utf-8")
                    else:
                        # Unsupported gcode.
                        # TODO: Need a way of raising an error.
                        print("Unsupported gcode: %s" % gcode, modal, modalFirst)
                        self._commandImmediate.put(b"!")
                        validGcode = False
                if validGcode:
                    self._commandStreaming.put(jogCommandString)
            else:
                validGcode = True
                for gcode in sorted(command.gcode.gcodes):
                    modal = str(gcode.modal_copy()).encode("utf-8")
                    modalFirst = bytes([modal[0]])
                    if (modal not in self.SUPPORTED_GCODE and
                            modalFirst not in self.SUPPORTED_GCODE):
                        # Unsupported gcode.
                        # TODO: Need a way of raising an error.
                        print("Unsupported gcode: %s" % gcode, modal, modalFirst)
                        self._commandImmediate.put(b"!")
                        validGcode = False
                if validGcode:
                    self._commandStreaming.put(command.gcode)


    def earlyUpdate(self):
        """ Called early in the event loop, before events have been received. """
        if self.connectionStatus != self.desiredConnectionStatus:
            # Transition between connection states.
            if self.connectionStatus is ConnectionState.CONNECTING:
                # Connection process already started.
                self.onConnected()

            elif self.connectionStatus is ConnectionState.DISCONNECTING:
                # Trying to diconnect.
                self.onDisconnected()

            elif self.connectionStatus in [
                    ConnectionState.FAIL, ConnectionState.MISSING_RESOURCE]:
                # A serial port error occurred either # while opening a serial port or
                # on an already open port.
                self.setDesiredConnectionStatus(ConnectionState.NOT_CONNECTED)
                self.setConnectionStatus(ConnectionState.CLEANUP)

            elif self.desiredConnectionStatus is ConnectionState.CONNECTED:
                # Start connection process.
                self.connect()

            elif self.desiredConnectionStatus is ConnectionState.NOT_CONNECTED:
                # Start disconnection.
                self.disconnect()
        
        if self.connectionStatus is ConnectionState.CONNECTED:
            if not self.state.eventFired:
                # Display debug info: Summary of machine state.
                self.publishOneByValue(self.keyGen("state"), self.state)
                self.state.eventFired = True

        # Process data received over serial port.
        receivedLine = None
        try:
            receivedLine = self._receivedData.get(block=False)
        except Empty:
            pass
        if receivedLine is not None:
            print("receivedLine:", receivedLine)
            self.state.parseIncoming(receivedLine)

    def update(self):
        super().update()

        if self._queuedUpdates:
            # Process local buffer.
            for update in self._queuedUpdates:
                self.doCommand(update)
            self._queuedUpdates.clear()

