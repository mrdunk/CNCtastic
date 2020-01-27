#!/usr/bin/env python3

""" Testing Grbl controller plugin. """

#pylint: disable=protected-access

import sys
import os
TESTDIR = os.path.dirname(__file__)
SRCDIR = '../'
sys.path.insert(0, os.path.abspath(os.path.join(TESTDIR, SRCDIR)))

import unittest

from definitions import ConnectionState
from controllers.grbl_1_1 import Grbl1p1Controller


class MockSerial:
    """ Mock version of "serial" library. """

    def __init__(self):
        self.dummy_data = []
        self.received_data = []

    def readline(self):  # pylint: disable=C0103
        """ Do nothing or return specified value for method. """
        if self.dummy_data:
            return self.dummy_data.pop(0)
        return None

    def write(self, data):
        """ Record paramiter for method. """
        self.received_data.append(data)

    def inWaiting(self) -> bool:  # pylint: disable=C0103
        """ Do nothing or return specified value for method. """
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
        self.controller.connectionStatus = ConnectionState.CONNECTED
        self.controller.desiredConnectionStatus = ConnectionState.CONNECTED
        self.controller.state.changesMade = False
        self.controller.testing = True

        self.assertTrue(self.controller._commandImmediate.empty())
        self.assertTrue(self.controller._commandStreaming.empty())
        self.assertTrue(self.controller._receivedData.empty())
        self.assertEqual(self.controller._errorCount, 0)
        self.assertEqual(self.controller._okCount, 0)

    def test_basic(self):
        """ Basic input as would be seen when everything is going perfectly. """
        self.controller._serial.dummy_data = [b"test\r\n", b"test2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_two_in_one(self):
        """ 2 input lines are received in a single cycle. """
        self.controller._serial.dummy_data = [b"test\r\ntest2\r\n", b"test3\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 3)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")
        self.assertEqual(self.controller._receivedData.get(), b"test3")

    def test_split_line(self):
        """ A line is split over 2 reads. """
        self.controller._serial.dummy_data = [b"te", b"st\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)

        self.assertEqual(self.controller._receivedData.get(), b"test")

    def test_split_line_before_eol(self):
        """ A line is split over 2 reads between content and EOL. """
        self.controller._serial.dummy_data = [b"test", b"\r\ntest2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_split_line_mid_eol(self):
        """ A line is split over 2 reads between EOL chars. """
        self.controller._serial.dummy_data = [b"test\r", b"\ntest2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_delayed_input(self):
        """ A line is split over 2 reads with empty read in between. """
        self.controller._serial.dummy_data = [b"te", None, b"st\r\n", None, b"test2\r\n"]
        self.controller._periodicIO()
        self.controller._periodicIO()  # "None" in data stopped read loop.
        self.controller._periodicIO()  # "None" in data stopped read loop.
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_empty_line(self):
        """ Empty line are ignored. """
        self.controller._serial.dummy_data = [b"\r\n", b"\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)

        self.controller._serial.dummy_data = [b"\r\n", b"\r\n", b"test\r\n", b"\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)

        self.controller._serial.dummy_data = []
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)

        self.assertEqual(self.controller._receivedData.get(), b"test")

    def test_receive_ok(self):
        """ Lines starting with "ok" are handled in the local thread.
        They change counters relating to current buffer state; As "ok" arrives,
        we know a buffer entry has been consumed. """
        self.controller._serial.dummy_data = [b"test\r\n", b"ok\r\n", b"test2\r\n", b"ok\r\n"]
        self.controller._sendBufLens.append(5)
        self.controller._sendBufActns.append(("dummy", None))
        self.controller._sendBufLens.append(10)
        self.controller._sendBufActns.append(("dummy", None))
        self.controller._sendBufLens.append(20)
        self.controller._sendBufActns.append(("dummy", None))

        self.controller._periodicIO()
        # 1 "ok" processed. Entry removed from _bufferLengths.
        self.assertEqual(len(self.controller._sendBufLens), 1)
        self.assertEqual(self.controller._okCount, 2)
        # 2 other messages.
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_receive_error(self):
        """ Lines starting with "error:" are handled in the local thread.
        Errors should halt execution imidiately. ("!" halts the machine in GRBL."""
        self.controller._serial.dummy_data = [
            b"test\r\n", b"error:12\r\n", b"test2\r\n", b"error:42\r\n"]
        self.controller._sendBufLens.append(5)
        self.controller._sendBufActns.append(("dummy", None))
        self.controller._sendBufLens.append(10)
        self.controller._sendBufActns.append(("dummy", None))

        self.controller._periodicIO()
        self.assertEqual(self.controller._errorCount, 2)
        # Errors are passed to the parent thread as well as being dealt with here.
        self.assertEqual(self.controller._receivedData.qsize(), 4)

        self.assertEqual(self.controller._serial.received_data[-1], b"!")
        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"error:12")
        self.assertEqual(self.controller._receivedData.get(), b"test2")
        self.assertEqual(self.controller._receivedData.get(), b"error:42")

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
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 4)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test 2")
        self.assertEqual(self.controller._receivedData.get(), b"test\t3")
        self.assertEqual(self.controller._receivedData.get(), b"test\n4")


class TestControllerSendDataToSerial(unittest.TestCase):
    """ Send data to controller over serial port. """

    def setUp(self):
        self.controller = Grbl1p1Controller()
        self.controller._serial = MockSerial()
        self.controller._time = MockTime()
        self.controller.connectionStatus = ConnectionState.CONNECTED
        self.controller.desiredConnectionStatus = ConnectionState.CONNECTED
        self.controller.state.changesMade = False
        self.controller.testing = True

        self.assertTrue(self.controller._commandImmediate.empty())
        self.assertTrue(self.controller._commandStreaming.empty())
        self.assertTrue(self.controller._receivedData.empty())
        self.assertEqual(self.controller._errorCount, 0)
        self.assertEqual(self.controller._okCount, 0)

    def test_basic(self):
        """ Basic input as would be seen when everything is going perfectly. """
        self.controller._serial.dummy_data = []
        # toSend = [b"G0 F100 X10 Y-10", b"!"]

        self.controller._periodicIO()
        # TODO


if __name__ == '__main__':
    unittest.main()
