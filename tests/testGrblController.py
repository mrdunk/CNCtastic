#!/usr/bin/env python3

import sys, os
testdir = os.path.dirname(__file__)
srcdir = '../'
sys.path.insert(0, os.path.abspath(os.path.join(testdir, srcdir)))

import unittest

from definitions import ConnectionState
from controllers.grbl_1_1 import Grbl1p1Controller


class MockSerial:
    def __init__(self):
        self.dummyData = []
        self.receivedData = []

    def readline(self):
        if self.dummyData:
            return self.dummyData.pop(0)
        return None

    def write(self, data):
        self.receivedData.append(data)


class MockTime:
    def __init__(self):
        self.returnValues = []

    def time(self):
        if self.returnValues:
            return self.returnValues.pop(0)
        return 0

    def sleep(self, value):
        return

class TestControllerReceiveData(unittest.TestCase):
    def setUp(self):
        self.controller = Grbl1p1Controller()
        self.controller._serial = MockSerial()
        self.controller._time = MockTime()
        self.controller.connectionStatus = ConnectionState.CONNECTED
        self.controller.desiredConnectionStatus = ConnectionState.CONNECTED
        self.controller.state.eventFired = True
        self.controller.testing = True
        
        self.assertTrue(self.controller._commandImmediate.empty())
        self.assertTrue(self.controller._commandStreaming.empty())
        self.assertTrue(self.controller._receivedData.empty())
        self.assertEqual(self.controller._errorCount, 0)
        self.assertEqual(self.controller._okCount, 0)

    def test_Basic(self):
        """ Basic input as would be seen when everything is going perfectly. """
        self.controller._serial.dummyData = [b"test\r\n", b"test2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_TwoInOne(self):
        """ 2 input lines are received in a single cycle. """
        self.controller._serial.dummyData = [b"test\r\ntest2\r\n", b"test3\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 3)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")
        self.assertEqual(self.controller._receivedData.get(), b"test3")

    def test_SplitLine(self):
        """ A line is split over 2 reads. """
        self.controller._serial.dummyData = [b"te", b"st\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)

        self.assertEqual(self.controller._receivedData.get(), b"test")

    def test_DelayedInput(self):
        """ A line is split over 2 reads with empty read in between. """
        self.controller._serial.dummyData = [b"te", None, b"st\r\n", None, b"test2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_EmptyLine(self):
        """ Empty line are ignored. """
        self.controller._serial.dummyData = [
                b"\r\n", b"\r\n", b"test\r\n", b"\r\n", b"test2\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 0)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")

    def test_okAndError(self):
        """ Lines starting with "ok" and "error:" are handled differently. """
        self.controller._serial.dummyData = [
                b"test\r\n",
                b"ok\r\n", b"ok\r\n",
                b"test2\r\n",
                b"error:1\r\n", b"error:42\r\n"]
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        # "ok" is handled in the local thread and not pushed to the buffer.
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.assertEqual(self.controller._okCount, 1)
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 1)
        self.assertEqual(self.controller._okCount, 2)
        # Back to "normal" string."
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 2)
        # Now errors.
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 3)
        self.assertEqual(self.controller._errorCount, 1)
        self.assertEqual(len(self.controller._serial.receivedData), 1)
        self.assertEqual(self.controller._serial.receivedData[-1], b"!")
        self.controller._periodicIO()
        self.assertEqual(self.controller._receivedData.qsize(), 4)
        self.assertEqual(self.controller._errorCount, 2)
        self.assertEqual(len(self.controller._serial.receivedData), 2)
        self.assertEqual(self.controller._serial.receivedData[-1], b"!")

        self.assertEqual(self.controller._receivedData.get(), b"test")
        self.assertEqual(self.controller._receivedData.get(), b"test2")
        self.assertEqual(self.controller._receivedData.get(), b"error:1")
        self.assertEqual(self.controller._receivedData.get(), b"error:42")




if __name__ == '__main__':
    unittest.main()

