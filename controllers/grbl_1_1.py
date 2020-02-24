# Pylint seems to be looking at python2.7's PySimpleGUI libraries so we need the following:
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" A plugin to support Grbl 1.1 controller hardware. """

from typing import List, Any, Optional, Deque, Tuple

import time
from queue import Queue, Empty
from collections import deque

from pygcode import GCode, Block
#import PySimpleGUIQt as sg
from terminals.gui import sg

from definitions import ConnectionState, FlagState
from interfaces._interface_base import UpdateState
from controllers._controller_serial_base import _SerialControllerBase
from controllers.state_machine import StateMachineGrbl as State

REPORT_INTERVAL = 1.0 # seconds
SERIAL_INTERVAL = 0.02 # seconds
RX_BUFFER_SIZE = 128

class Grbl1p1Controller(_SerialControllerBase):
    """ A plugin to support Grbl 1.1 controller hardware. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

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

    def __init__(self, label: str = "grbl1.1") -> None:
        super().__init__(label)

        # Allow replacing with a mock version when testing.
        self._time: Any = time

        # State machine to track current GRBL state.
        self.state = State(self.publish_from_here)

        # Populate with GRBL commands that are processed immediately and don't need queued.
        self._command_immediate: Queue[bytes] = Queue()
        # Populate with GRBL commands that are processed sequentially.
        self._command_streaming: Queue[bytes] = Queue()

        # Data received from GRBL that does not need processed immediately.
        self._received_data: Queue[bytes] = Queue()

        self._partial_read: bytes = b""
        self._last_write: float = 0
        self._error_count: int = 0
        self._ok_count: int = 0
        self._send_buf_lens: Deque[int] = deque()
        self._send_buf_actns: Deque[Tuple[bytes, Any]] = deque()

        """ Certain gcode commands write to EPROM which disabled interrupts which
        would interfere with serial IO. When one of these commands is executed we
        should pause before continuing with serial IO. """
        self.flush_before_continue = False

    def _complete_before_continue(self, command: bytes) -> bool:
        """ Certain gcode commands write to EPROM which disabled interrupts which
        would interfere with serial IO. When one of these commands is executed we
        should pause before continuing with serial IO. """
        for slow_command in self.SLOWCOMMANDS:
            if slow_command in command:
                return True
        return False

    def gui_layout(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        layout = [
            [sg.Text("Title:", size=(20, 1)),
             sg.Text("unknown", key=self.key_gen("label"), size=(20, 1)),
             sg.Checkbox("Active", default=self.active, key=self.key_gen("active"))],
            [sg.Text("Connection state:", size=(20, 1)),
             sg.Text(size=(18, 1), key=self.key_gen("connection_status"))],
            [sg.Text("Desired:", size=(20, 1)),
             sg.Text(size=(18, 1), key=self.key_gen("desired_connection_status"))],
            [sg.Multiline(default_text="Machine state", size=(60, 10),
                          key=self.key_gen("state"),
                          autoscroll=True, disabled=True)],
            [sg.Button('Connect', key=self.key_gen("connect"), size=(10, 1), pad=(2, 2)),
             sg.Button('Disconnect', key=self.key_gen("disconnect"), size=(10, 1), pad=(2, 2)),
             sg.Exit(size=(10, 1), pad=(2, 2))
             ],
            ]
        return layout

    def parse_incoming(self, incoming: Optional[bytes]) -> None:
        """ Process data received from serial port.
        Handles urgent updates here and puts the rest in _received_data buffer for
        later processing. """
        if incoming is None:
            incoming = b""
        if self._partial_read:
            incoming = self._partial_read + incoming

        if not incoming:
            return

        pos = incoming.find(b"\r\n")
        if pos < 0:
            self._partial_read = incoming
            return

        tmp_incoming = incoming[:pos + 2]
        self._partial_read = incoming[pos + 2:]
        incoming = tmp_incoming

        incoming = incoming.strip()
        if not incoming:
            return

        # Handle time critical responses here. Otherwise defer to main thread.
        if incoming.startswith(b"error:"):
            self._incoming_error(incoming)
            self._received_data.put(incoming)
        elif incoming.startswith(b"ok"):
            self._incoming_ok()
        else:
            self._received_data.put(incoming)

    def _incoming_error(self, incoming: bytes) -> None:
        """ Called when GRBL returns an "error:". """
        self._error_count += 1
        self._send_buf_lens.popleft()
        action = self._send_buf_actns.popleft()
        print("error: '%s' due to '%s' " % (incoming.decode("utf-8"), action[0].decode("utf-8")))
        # Feed Hold:
        self._command_immediate.put(b"!")

    def _incoming_ok(self) -> None:
        """ Called when GRBL returns an "ok". """
        if not self._send_buf_lens:
            return
        self._ok_count += 1
        self._send_buf_lens.popleft()
        action = self._send_buf_actns.popleft()
        print("'ok' acknowledges: %s" % action[0].decode("utf-8"), type(action[1]))
        if isinstance(action[1], GCode):
            self._received_data.put(b"[sentGcode:%s]" % \
                                    str(action[1].modal_copy()).encode("utf-8"))

    def _write_immediate(self) -> bool:
        """ Write entries in the _command_immediate buffer to serial port. """
        task = None
        try:
            task = self._command_immediate.get(block=False)
        except Empty:
            return False

        #print("_write_immediate", task)
        return self._serial_write(task)

    def _write_streaming(self) -> bool:
        """ Write entries in the _command_streaming buffer to serial port. """
        if self.flush_before_continue and sum(self._send_buf_lens) == 0:
            self.flush_before_continue = False

        if self._send_buf_lens:
            return False

        if sum(self._send_buf_lens) >= RX_BUFFER_SIZE - 1:
            return False

        task = None
        try:
            task = self._command_streaming.get(block=False)
        except Empty:
            return False

        task_string = task
        if isinstance(task, Block):
            task_string = str(task).encode("utf-8")

        if self._complete_before_continue(task_string):
            self.flush_before_continue = True

        #print("_write_streaming", task_string)
        if self._serial_write(task_string + b"\n"):
            self._send_buf_lens.append(len(task_string) + 1)
            self._send_buf_actns.append((task_string, task))
            return True
        return False

    def _periodic_io(self) -> None:
        """ Read from and write to serial port.
            Called from a separate thread.
            Blocks while serial port remains connected. """
        while self.connection_status is ConnectionState.CONNECTED:
            # Read
            read = self._serial_read()
            while read or (b"\r\n" in self._partial_read):
                self.parse_incoming(read)
                read = self._serial_read()

            #Write
            if not self._write_immediate():
                self._write_streaming()

            # Request status update periodically.
            if self._last_write < self._time.time() - REPORT_INTERVAL:
                self._command_immediate.put(b"?")
                self._last_write = self._time.time()

                #print("Receive buffer contains %s commands, %s bytes" %
                #        (len(self._send_buf_lens), sum(self._send_buf_lens)))
            self._time.sleep(SERIAL_INTERVAL)

            if self.testing:
                break

    def do_command(self, command: UpdateState) -> None:
        """ Turn update received via event into something GRBL can parse and put
        in a command buffer. """
        assert isinstance(command, UpdateState)
        print(command)

        # Flags.
        if command.pause is FlagState.TRUE and not self.state.pause:
            # GRBL feed hold.
            self._command_immediate.put(b"!")
        elif command.pause is FlagState.FALSE and self.state.pause:
            if not self.state.parking:
                # GRBL Cycle Start / Resume
                self._command_immediate.put(b"~")

        if command.door is FlagState.TRUE and not self.state.door:
            # GRBL Safety Door.
            self._command_immediate.put(chr(0x84).encode("utf-8"))
        elif command.door is FlagState.FALSE and self.state.door:
            if not self.state.parking:
                # GRBL Cycle Start / Resume
                self._command_immediate.put(b"~")

        if command.gcode is None:
            return

        # Gcode
        if command.jog is FlagState.TRUE:
            valid_gcode = True
            jog_command_string = b"$J="
            for gcode in sorted(command.gcode.gcodes):
                modal = str(gcode.modal_copy()).encode("utf-8")
                modal_first = bytes([modal[0]])
                if (modal in self.SUPPORTED_JOG_GCODE or
                        modal_first in self.SUPPORTED_JOG_GCODE):
                    jog_command_string += str(gcode).encode("utf-8")
                elif modal in [b"G00", b"G0", b"G01", b"G1"]:
                    for param, value in gcode.get_param_dict().items():
                        jog_command_string += param.encode("utf-8")
                        jog_command_string += str(value).encode("utf-8")
                else:
                    # Unsupported gcode.
                    # TODO: Need a way of raising an error.
                    print("Unsupported gcode: %s" % gcode, modal, modal_first)
                    # GRBL feed hold.
                    self._command_immediate.put(b"!")
                    valid_gcode = False
            if valid_gcode:
                self._command_streaming.put(jog_command_string)
        else:
            valid_gcode = True
            # TODO: Use self.isGcodeSupported()
            for gcode in sorted(command.gcode.gcodes):
                modal = str(gcode.modal_copy()).encode("utf-8")
                modal_first = bytes([modal[0]])
                if (modal not in self.SUPPORTED_GCODE and
                        modal_first not in self.SUPPORTED_GCODE):
                    # Unsupported gcode.
                    # TODO: Need a way of raising an error.
                    print("Unsupported gcode: %s" % gcode, modal, modal_first)
                    # GRBL feed hold.
                    self._command_immediate.put(b"!")
                    valid_gcode = False
            if valid_gcode:
                self._command_streaming.put(command.gcode)

    def early_update(self) -> None:
        """ Called early in the event loop, before events have been received. """
        super().early_update()

        # Process data received over serial port.
        received_line = None
        try:
            received_line = self._received_data.get(block=False)
        except Empty:
            pass
        if received_line is not None:
            #print("received_line:", received_line)
            self.state.parse_incoming(received_line)

        # Display debug info: Summary of machine state.
        if self.connection_status is ConnectionState.CONNECTED:
            if self.state.changes_made:
                self.publish_one_by_value(self.key_gen("state"), self.state)
                self.state.changes_made = False

    def update(self) -> None:
        """ Called by the coordinator after events have been delivered. """
        super().update()

        if self._queued_updates:
            # Process local buffer.
            for update in self._queued_updates:
                self.do_command(update)
            self._queued_updates.clear()

    def on_connected(self) -> None:
        """ Executed when serial port first comes up. """
        super().on_connected()

        # Request a report on the modal state of the GRBL controller.
        self._command_streaming.put(b"$G")
        # Grbl settings report.
        self._command_streaming.put(b"$$")

    def on_activate(self) -> None:
        """ Called whenever self.active is set True. """
        if self.connection_status is ConnectionState.CONNECTED:
            # The easiest way to replay the following events is to just request
            # the data from the Grbl controller again.
            # This way the events get re-sent when fresh data arrives.
            # (The alternative would be to have the StateMchine re-send the
            # cached data.)

            # Request a report on the modal state of the GRBL controller.
            #self._command_streaming.put(b"$G")
            # Grbl settings report.
            #self._command_streaming.put(b"$$")

            self.state.sync()
