#!/usr/bin/env python3

""" Testing Grbl controller plugin. """

#pylint: disable=protected-access

import unittest
import loader  # pylint: disable=E0401,W0611
from definitions import ConnectionState
from controllers.grbl_1_1 import Grbl1p1Controller, RX_BUFFER_SIZE, REPORT_INTERVAL


class MockSerial:
    """ Mock version of serial port. """

    def __init__(self):
        self.dummy_data = []
        self.written_data = []

    def readline(self):  # pylint: disable=C0103
        """ Do nothing or return specified value for method. """
        if self.dummy_data:
            return self.dummy_data.pop(0)
        return None

    def write(self, data):
        """ Record paramiter for method. """
        self.written_data.append(data)

    def inWaiting(self) -> bool:  # pylint: disable=C0103
        """ Mock version of method. """
        return bool(self.dummy_data)


class MockTime:
    """ Mock version of "time" library. """

    def __init__(self):
        self.return_values = []

    def time(self):
        """ Do nothing or return specified value for method. """
        if self.return_values:
            return self.return_values.pop(0)
        return 0

    def sleep(self, value):  # pylint: disable=R0201, W0613
        """ Do nothing for sleep method. """
        return


class TestControllerReceiveDataFromSerial(unittest.TestCase):
    """ Parsing data received over serial port. """

    def setUp(self):
        self.controller = Grbl1p1Controller()
        self.controller._serial = MockSerial()
        self.controller._time = MockTime()
        self.controller.connection_status = ConnectionState.CONNECTED
        self.controller.desired_connection_status = ConnectionState.CONNECTED
        self.controller.state.changes_made = False
        self.controller.first_receive = False
        self.controller.testing = True

        self.assertTrue(self.controller._command_immediate.empty())
        self.assertTrue(self.controller._command_streaming.empty())
        self.assertTrue(self.controller._received_data.empty())
        self.assertEqual(self.controller._error_count, 0)
        self.assertEqual(self.controller._ok_count, 0)

    def test_basic(self):
        """ Basic input as would be seen when everything is going perfectly. """
        self.controller._serial.dummy_data = [b"test\r\n", b"test2\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 2)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")

    def test_two_in_one(self):
        """ 2 input lines are received in a single cycle. """
        self.controller._serial.dummy_data = [b"test\r\ntest2\r\n", b"test3\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 3)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")
        self.assertEqual(self.controller._received_data.get(), b"test3")

    def test_split_line(self):
        """ A line is split over 2 reads. """
        self.controller._serial.dummy_data = [b"te", b"st\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 1)

        self.assertEqual(self.controller._received_data.get(), b"test")

    def test_split_line_before_eol(self):
        """ A line is split over 2 reads between content and EOL. """
        self.controller._serial.dummy_data = [b"test", b"\r\ntest2\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 2)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")

    def test_split_line_mid_eol(self):
        """ A line is split over 2 reads between EOL chars. """
        self.controller._serial.dummy_data = [b"test\r", b"\ntest2\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 2)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")

    def test_delayed_input(self):
        """ A line is split over 2 reads with empty read in between. """
        self.controller._serial.dummy_data = [b"te", None, b"st\r\n", None, b"test2\r\n"]
        self.controller._periodic_io()
        self.controller._periodic_io()  # "None" in data stopped read loop.
        self.controller._periodic_io()  # "None" in data stopped read loop.
        self.assertEqual(self.controller._received_data.qsize(), 2)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")

    def test_empty_line(self):
        """ Empty line are ignored. """
        self.controller._serial.dummy_data = [b"\r\n", b"\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 0)

        self.controller._serial.dummy_data = [b"\r\n", b"\r\n", b"test\r\n", b"\r\n"]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 1)

        self.controller._serial.dummy_data = []
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 1)

        self.assertEqual(self.controller._received_data.get(), b"test")

    def test_receive_ok(self):
        """ Lines starting with "ok" are handled in the local thread.
        They change counters relating to current buffer state; As "ok" arrives,
        we know a buffer entry has been consumed. """
        self.controller._serial.dummy_data = [b"test\r\n", b"ok\r\n", b"test2\r\n", b"ok\r\n"]
        self.controller._send_buf_lens.append(5)
        self.controller._send_buf_actns.append((b"dummy", None))
        self.controller._send_buf_lens.append(10)
        self.controller._send_buf_actns.append((b"dummy", None))
        self.controller._send_buf_lens.append(20)
        self.controller._send_buf_actns.append((b"dummy", None))

        self.controller._periodic_io()

        # 1 "ok" processed. Entry removed from _bufferLengths.
        self.assertEqual(len(self.controller._send_buf_lens), 1)
        self.assertEqual(self.controller._ok_count, 2)
        # 2 other messages.
        self.assertEqual(self.controller._received_data.qsize(), 2)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test2")

    def test_receive_error(self):
        """ Lines starting with "error:" are handled in the local thread.
        Errors should halt execution imidiately. ("!" halts the machine in GRBL."""
        self.controller._serial.dummy_data = [
            b"test\r\n", b"error:12\r\n", b"test2\r\n", b"error:42\r\n"]
        self.controller._send_buf_lens.append(5)
        self.controller._send_buf_actns.append((b"dummy", None))
        self.controller._send_buf_lens.append(10)
        self.controller._send_buf_actns.append((b"dummy", None))

        self.controller._periodic_io()
        self.assertEqual(self.controller._error_count, 2)
        # Errors are passed to the parent thread as well as being dealt with here.
        self.assertEqual(self.controller._received_data.qsize(), 4)

        self.assertEqual(self.controller._serial.written_data[-1], b"!")
        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"error:12")
        self.assertEqual(self.controller._received_data.get(), b"test2")
        self.assertEqual(self.controller._received_data.get(), b"error:42")

    def test_whitespace(self):
        """ Whitespace should be stripped from ends of lines but not middle. """
        self.controller._serial.dummy_data = [b"  test  \r\n",
                                              b"test 2\r\n",
                                              b"    \r\n",
                                              b"\t\r\n",
                                              b"\n\r\n",
                                              b"\r\r\n",
                                              b"test\t3\r\n",
                                              b"\ntest\n4\n\r\n",
                                              ]
        self.controller._periodic_io()
        self.assertEqual(self.controller._received_data.qsize(), 4)

        self.assertEqual(self.controller._received_data.get(), b"test")
        self.assertEqual(self.controller._received_data.get(), b"test 2")
        self.assertEqual(self.controller._received_data.get(), b"test\t3")
        self.assertEqual(self.controller._received_data.get(), b"test\n4")


class TestControllerSendDataToSerial(unittest.TestCase):
    """ Send data to controller over serial port. """

    def setUp(self):
        self.controller = Grbl1p1Controller(_time = MockTime())
        self.controller._serial = MockSerial()
        self.controller.connection_status = ConnectionState.CONNECTED
        self.controller.desired_connection_status = ConnectionState.CONNECTED
        self.controller.state.changes_made = False
        self.controller.first_receive = False
        self.controller.testing = True

        self.assertTrue(self.controller._command_immediate.empty())
        self.assertTrue(self.controller._command_streaming.empty())
        self.assertTrue(self.controller._received_data.empty())
        self.assertEqual(self.controller._error_count, 0)
        self.assertEqual(self.controller._ok_count, 0)

    def test_immediate(self):
        """ Some commands should be processed as soon as they arrive on the serial
            port. """
        self.controller._command_immediate.put("test command")
        self.controller._command_immediate.put("test command 2")
        self.assertFalse(self.controller._command_streaming.qsize())
        self.controller._serial.written_data = []

        # Process everything in the buffer.
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # Commands have been sent out serial port.
        self.assertEqual(self.controller._serial.written_data[-2], "test command")
        self.assertEqual(self.controller._serial.written_data[-1], "test command 2")
        self.assertEqual(len(self.controller._serial.written_data), 2)

    def test_streaming_mode_fail(self):
        """ Controller may not be in both running_gcode and running_jog mode at
        the same time. """
        self.controller.running_gcode = True
        self.controller.running_jog = True

        with self.assertRaises(AssertionError):
            self.controller._periodic_io()

    def test_streaming_mode_transition_to_gcode(self):
        """ If no mode selected, allow transition to gcode mode. """
        self.controller.running_gcode = False
        self.controller.running_jog = False
        self.controller._command_streaming.put(b"G0 X0 Y0 F10")
        self.controller.state.machine_state = b"Idle"

        self.controller._periodic_io()

        self.assertTrue(self.controller.running_gcode)
        self.assertFalse(self.controller.running_jog)
        self.assertEqual(self.controller._serial.written_data[-1], b"G0X0Y0F10\n")
        self.assertEqual(len(self.controller._serial.written_data), 1)

    def test_streaming_mode_transition_to_gcode_from_jog_1(self):
        """ if in jog mode, cancel any active Jog command and transition to gcode
        mode. """
        self.controller.running_gcode = False
        self.controller.running_jog = True
        self.controller._command_streaming.put(b"G0 X0 Y0 F10")
        self.controller.state.machine_state = b"Jog"

        self.controller._periodic_io()

        self.assertTrue(self.controller.running_gcode)
        self.assertFalse(self.controller.running_jog)
        # Cancel Jog = b"\x85"
        self.assertEqual(self.controller._serial.written_data[-2], b"\x85")
        self.assertEqual(self.controller._serial.written_data[-1], b"G0X0Y0F10\n")
        self.assertEqual(len(self.controller._serial.written_data), 2)

    def test_streaming_mode_transition_to_gcode_from_jog_2(self):
        """ if in jog mode, cancel any active Jog command and transition to gcode
        mode. """
        self.controller.running_gcode = False
        self.controller.running_jog = True
        self.controller._command_streaming.put(b"G0 X0 Y0 F10")
        self.controller.state.machine_state = b"Idle"

        self.controller._periodic_io()

        self.assertTrue(self.controller.running_gcode)
        self.assertFalse(self.controller.running_jog)
        # It is possible a jog command has been issued since
        # controller.state.machine_state has been updated.
        # Best to clear any jog command with b"\x85".
        self.assertEqual(self.controller._serial.written_data[-2], b"\x85")
        self.assertEqual(self.controller._serial.written_data[-1], b"G0X0Y0F10\n")
        self.assertEqual(len(self.controller._serial.written_data), 2)

    def test_streaming_mode_transition_to_jog(self):
        """ If no mode selected, allow transition to jog mode. """
        self.controller.running_gcode = False
        self.controller.running_jog = False
        # "$J=..." is a GRBL Jog command.
        self.controller._command_streaming.put(b"$J=X0Y0")
        self.controller.state.machine_state = b"Idle"

        self.controller._periodic_io()

        self.assertFalse(self.controller.running_gcode)
        self.assertTrue(self.controller.running_jog)
        self.assertEqual(self.controller._serial.written_data[-1], b"$J=X0Y0\n")
        self.assertEqual(len(self.controller._serial.written_data), 1)

    def test_streaming_mode_transition_to_jog_fail(self):
        """ if in gcode mode, do not allow transition to jog mode. """
        self.controller.running_gcode = True
        self.controller.running_jog = False
        # "$J=..." is a GRBL Jog command.
        self.controller._command_streaming.put(b"$J=X0Y0")
        self.controller.state.machine_state = b"Idle"

        self.controller._periodic_io()

        self.assertTrue(self.controller.running_gcode)
        self.assertFalse(self.controller.running_jog)
        self.assertEqual(len(self.controller._serial.written_data), 0)

    def test_streaming_mode_timeout(self):
        """ if in gcode mode but inactive for a while, allow transition to jog mode. """
        self.controller.running_gcode = True
        self.controller.running_jog = False
        self.running_mode_at = 1.0
        self.controller._time.return_values = [(1 + (3 * REPORT_INTERVAL))] * 2
        self.controller.state.machine_state = b"Idle"

        self.controller._periodic_io()

        self.assertFalse(self.controller.running_gcode)
        self.assertFalse(self.controller.running_jog)
        self.assertEqual(len(self.controller._serial.written_data), 0)

    def test_streaming_flush_before_continue(self):
        """ Any command in SLOWCOMMANDS should block until an acknowledgement has
        been received from the Grbl hardware. """
        self.controller._command_streaming.put(b"test command 1")
        self.controller._command_streaming.put(b"G59 A slow command")
        self.controller._command_streaming.put(b"test command 2")
        self.controller._serial.written_data = []

        # Process everything in the buffer.
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # Commands up to the slow command has been sent out serial port but
        # remaining command is still queued until the GRBL send buffer has been
        # drained.
        self.assertEqual(self.controller._serial.written_data[-2], b"testcommand1\n")
        self.assertEqual(self.controller._serial.written_data[-1], b"G59Aslowcommand\n")
        self.assertEqual(len(self.controller._serial.written_data), 2)

        # 2 commands have been sent and 2 have not been acknowledged yet.
        self.assertEqual(self.controller._ok_count, 0)
        self.assertEqual(len(self.controller._send_buf_lens), 2)

        # Simulate an "OK" being received acknowledges the 1st sent command
        self.controller._incoming_ok()
        self.controller._periodic_io()

        # 2 commands have been sent and 1 has not been acknowledged yet.
        self.assertEqual(self.controller._ok_count, 1)
        self.assertEqual(len(self.controller._send_buf_lens), 1)

        # Slow command still blocking the last command.
        self.assertEqual(self.controller._serial.written_data[-2], b"testcommand1\n")
        self.assertEqual(self.controller._serial.written_data[-1], b"G59Aslowcommand\n")
        self.assertEqual(len(self.controller._serial.written_data), 2)

        # Simulate an "OK" being received acknowledges the sent slow command
        self.controller._incoming_ok()
        self.controller._periodic_io()

        # Receiving the "OK" acknowledging the slow command unblocks the last command.
        # Now we should see all 3 commands having been sent.
        self.assertEqual(self.controller._serial.written_data[-3], b"testcommand1\n")
        self.assertEqual(self.controller._serial.written_data[-2], b"G59Aslowcommand\n")
        self.assertEqual(self.controller._serial.written_data[-1], b"testcommand2\n")
        self.assertEqual(len(self.controller._serial.written_data), 3)

        # Last command has been sent but has not been acknowledged yet.
        self.assertEqual(self.controller._ok_count, 2)
        self.assertEqual(len(self.controller._send_buf_lens), 1)

        # Simulate an "OK" being received acknowledges the last command
        self.controller._incoming_ok()

        # All pending commands have been acknowledged.
        self.assertEqual(self.controller._ok_count, 3)
        self.assertEqual(len(self.controller._send_buf_lens), 0)

    def test_max_send_buffer_size(self):
        """ Receive buffer never overflows.
        Grbl receive buffer has a known limited size. "OK" messages will be
        received when Grbl has processed a command and removed it from the buffer.
        """
        def str_len(strings):
            """ Returns the combined lengths of all strings in collection. """
            len_ = 0
            for s in strings:
                len_ += len(s)
            return len_

        # Fill most of the buffer.
        self.controller._command_streaming.put(b"a" * (RX_BUFFER_SIZE - 2))
        # Now some small commands.
        self.controller._command_streaming.put(b"b")
        self.controller._command_streaming.put(b"c")
        self.controller._command_streaming.put(b"d")

        # Process everything in the buffer.
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # First 2 commands made it out the serial port.
        self.assertEqual(len(self.controller._send_buf_lens), 2)
        # Recorded length of tracked data matches what went out the serial port.
        self.assertEqual(sum(self.controller._send_buf_lens),
                         str_len(self.controller._serial.written_data))
        # Next 2 commands still waiting to go.
        self.assertEqual(self.controller._command_streaming.qsize(), 2)

        # "OK" acknowledges the first command. Will now be space for the
        # remaining commands.
        self.controller._incoming_ok()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # Recorded length of tracked data matches what went out the serial port.
        self.assertEqual(sum(self.controller._send_buf_lens),
                str_len(self.controller._serial.written_data[1:]))
        # All commands have been sent.
        self.assertEqual(self.controller._command_streaming.qsize(), 0)

    def test_max_send_buffer_size_off_by_1(self):
        """ Receive buffer never overflows.
        Grbl receive buffer has a known limited size. "OK" messages will be
        received when Grbl has processed a command and removed it from the buffer.
        """
        def str_len(strings):
            """ Returns the combined lengths of all strings in collection. """
            len_ = 0
            for s in strings:
                len_ += len(s)
            return len_

        # Fill most of the buffer.
        self.controller._command_streaming.put(b"a" * (RX_BUFFER_SIZE - 3))
        # Now some small commands.
        self.controller._command_streaming.put(b"b")
        self.controller._command_streaming.put(b"c")
        self.controller._command_streaming.put(b"d")

        # Process everything in the buffer.
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # First 2 commands made it out the serial port.
        self.assertEqual(len(self.controller._send_buf_lens), 2)
        # Recorded length of tracked data matches what went out the serial port.
        self.assertEqual(sum(self.controller._send_buf_lens),
                         str_len(self.controller._serial.written_data))
        # Next 2 commands still waiting to go.
        self.assertEqual(self.controller._command_streaming.qsize(), 2)

        # "OK" acknowledges the first command. Will now be space for the
        # remaining commands.
        self.controller._incoming_ok()
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # Recorded length of tracked data matches what went out the serial port.
        self.assertEqual(sum(self.controller._send_buf_lens),
                str_len(self.controller._serial.written_data[1:]))
        # All commands have been sent.
        self.assertEqual(self.controller._command_streaming.qsize(), 0)

    def test_send_zero_lenght(self):
        """ Zero length commands should not be sent to Grbl. """
        self.controller._command_streaming.put(b"a")
        self.controller._command_streaming.put(b"")
        self.controller._command_streaming.put(b"c")

        # Process everything in the buffer.
        self.controller._periodic_io()
        self.controller._periodic_io()
        self.controller._periodic_io()

        # All commands have been sent.
        self.assertEqual(self.controller._command_streaming.qsize(), 0)

        # Only non-empty commands were actually sent.
        self.assertEqual(self.controller._serial.written_data[0], b"a\n")
        self.assertEqual(self.controller._serial.written_data[1], b"c\n")
        self.assertEqual(len(self.controller._serial.written_data), 2)
        self.assertEqual(sum(self.controller._send_buf_lens), 4)

if __name__ == "__main__":
    unittest.main()
