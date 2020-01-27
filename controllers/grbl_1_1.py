from typing import List, Any, Optional

import time
from queue import Queue, Empty
from collections import deque

#import PySimpleGUIQt as sg
from terminals.gui import sg
from pygcode import GCode, Block

from definitions import ConnectionState
from controllers._controllerSerialBase import _SerialControllerBase
from interfaces._interfaceBase import UpdateState
from controllers.stateMachine import StateMachineGrbl as State
from definitions import FlagState

REPORT_INTERVAL = 1.0 # seconds
SERIAL_INTERVAL = 0.02 # seconds
RX_BUFFER_SIZE = 128

className = "Grbl1p1Controller"

class Grbl1p1Controller(_SerialControllerBase):

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

    SLOWCOMMANDS = [b"G10 L2 ", b"G10 L20 ", b"G28.1 ", b"G30.1 ", b"$x=", b"$I=",
                    b"$Nx=", b"$RST=", b"G54 ", b"G55 ", b"G56 ", b"G57 ", b"G58 ",
                    b"G59 ", b"G28 ", b"G30 ", b"$$", b"$I", b"$N", b"$#"]

    def __init__(self, label: str="grbl1.1") -> None:
        super().__init__(label)

        # Allow replacing with a mock version when testing.
        self._time: Any = time

        # State machine to track current GRBL state.
        self.state = State(self.publishFromHere)

        # Populate with GRBL commands that are processed immediately and don't need queued.
        self._commandImmediate: Queue = Queue()
        # Populate with GRBL commands that are processed sequentially.
        self._commandStreaming: Queue = Queue()

        # Data received from GRBL that does not need processed immediately.
        self._receivedData: Queue = Queue()

        self._partialRead: bytes = b""
        self._lastWrite: float = 0
        self._errorCount: int = 0
        self._okCount: int = 0
        self._sendBufLens: deque = deque()
        self._sendBufActns: deque = deque()

        """ Certain gcode commands write to EPROM which disabled interrupts which
        would interfere with serial IO. When one of these commands is executed we
        should pause before continuing with serial IO. """
        self.flushBeforeContinue = False

    def _completeBeforeContinue(self, command: bytes) -> bool:
        """ Certain gcode commands write to EPROM which disabled interrupts which
        would interfere with serial IO. When one of these commands is executed we
        should pause before continuing with serial IO. """
        for slowCommand in self.SLOWCOMMANDS:
            if slowCommand in command:
                return True
        return False

    def publishFromHere(self, variableName: str, variableValue: Any) -> None:
        self.publish_one_by_value(self.key_gen(variableName), variableValue)
        
    def guiLayout(self) -> List:
        layout = [
                [sg.Text("Title:", size=(20,1)),
                    sg.Text("unknown", key=self.key_gen("label"), size=(20,1)),
                    sg.Checkbox("Active", default=self.active, key=self.key_gen("active"))],
                [sg.Text("Connection state:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.key_gen("connectionStatus"))],
                [sg.Text("Desired:", size=(20,1)),
                    sg.Text(size=(18,1), key=self.key_gen("desiredConnectionStatus"))],
                [sg.Multiline(default_text="Machine state", size=(60, 10),
                              key=self.key_gen("state"),
                              autoscroll=True, disabled=True)],
                [
                    sg.Button('Connect', key=self.key_gen("connect"), size=(10, 1), pad=(2, 2)),
                    sg.Button('Disconnect', key=self.key_gen("disconnect"),
                              size=(10, 1), pad=(2, 2)),
                    sg.Exit(size=(10, 1), pad=(2, 2))
                    ],
                ]
        return layout
    
    def parseIncoming(self, incoming: Optional[bytes]) -> None:
        """ Process data received from serial port.
        Handles urgent updates here and puts the rest in _receivedData buffer for
        later processing. """
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

    def _incomingError(self, incoming: bytes) -> None:
        """ Called when GRBL returns an "error:". """
        self._errorCount += 1
        self._sendBufLens.popleft()
        action = self._sendBufActns.popleft()
        print("error: '%s' due to '%s' " % (incoming, action[0]))
        # Feed Hold:
        self._commandImmediate.put(b"!")

    def _incomingOk(self, incoming: bytes) -> None:
        """ Called when GRBL returns an "ok". """
        if not self._sendBufLens:
            return
        self._okCount += 1
        self._sendBufLens.popleft()
        action = self._sendBufActns.popleft()
        print("'ok' acknowledges: %s" % action[0], type(action[1]))
        if isinstance(action[1], GCode):
            self._receivedData.put(b"[sentGcode:%s]" % str(action.modal_copy()).encode("utf-8"))

    def _writeImmediate(self) -> bool:
        """ Write entries in the _commandImmediate buffer to serial port. """
        task = None
        try:
            task = self._commandImmediate.get(block=False)
        except Empty:
            return False

        #print("_writeImmediate", task)
        return self._serialWrite(task)

    def _writeStreaming(self) -> bool:
        """ Write entries in the _commandStreaming buffer to serial port. """
        if self.flushBeforeContinue and sum(self._sendBufLens) == 0:
            self.flushBeforeContinue = False

        if self._sendBufLens:
            return False

        if sum(self._sendBufLens) >= RX_BUFFER_SIZE - 1:
            return False

        task = None
        try:
            task = self._commandStreaming.get(block=False)
        except Empty:
            return False

        if self._completeBeforeContinue(task):
            self.flushBeforeContinue = True

        taskString = task
        if isinstance(task, Block):
            taskString = str(task).encode("utf-8")

        #print("_writeStreaming", taskString)
        if self._serialWrite(taskString + b"\n"):
            self._sendBufLens.append(len(taskString) + 1)
            self._sendBufActns.append((taskString, task))
            return True
        return False

    def _periodicIO(self) -> None:
        """ Read from and write to serial port.
            Called from a separate thread.
            Blocks while serial port remains connected. """
        while self.connectionStatus is ConnectionState.CONNECTED:
            # Read
            read = self._serialRead()
            while read or (b"\r\n" in self._partialRead):
                self.parseIncoming(read)
                read = self._serialRead()

            #Write
            if not self._writeImmediate():
                self._writeStreaming()

            # Request status update periodically.
            if self._lastWrite < self._time.time() - REPORT_INTERVAL:
                self._commandImmediate.put(b"?")
                self._lastWrite = self._time.time()

                #print("Receive buffer contains %s commands, %s bytes" %
                #        (len(self._sendBufLens), sum(self._sendBufLens)))
            self._time.sleep(SERIAL_INTERVAL)

            if self.testing:
                break

    def doCommand(self, command: UpdateState) -> None:
        """ Turn update received via event into something GRBL can parse and put
        in a command buffer. """
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


    def early_update(self) -> None:
        """ Called early in the event loop, before events have been received. """
        super().early_update()

        # Process data received over serial port.
        receivedLine = None
        try:
            receivedLine = self._receivedData.get(block=False)
        except Empty:
            pass
        if receivedLine is not None:
            #print("receivedLine:", receivedLine)
            self.state.parseIncoming(receivedLine)

        # Display debug info: Summary of machine state.
        if self.connectionStatus is ConnectionState.CONNECTED:
            if self.state.changesMade:
                self.publish_one_by_value(self.key_gen("state"), self.state)
                self.state.changesMade = False

    def update(self) -> None:
        """ Called by the coordinator after events have been delivered. """
        super().update()

        if self._queuedUpdates:
            # Process local buffer.
            for update in self._queuedUpdates:
                self.doCommand(update)
            self._queuedUpdates.clear()
    
    def onConnected(self) -> None:
        """ Executed when serial port first comes up. """
        super().onConnected()
        
        # Request a report on the modal state of the GRBL controller.
        self._commandStreaming.put(b"$G")
        # Grbl settings report.
        self._commandStreaming.put(b"$$")

    def onActivate(self) -> None:
        """ Called whenever self.active is set True. """
        if self.connectionStatus is ConnectionState.CONNECTED:
            # The easiest way to replay the following events is to just request
            # the data from the Grbl controller again.
            # This way the events get re-sent when fresh data arrives.
            # (The alternative would be to have the StateMchine re send the
            # cached data.)

            # Request a report on the modal state of the GRBL controller.
            #self._commandStreaming.put(b"$G")
            # Grbl settings report.
            #self._commandStreaming.put(b"$$")

            self.state.sync()

