#!/usr/bin/env python3

""" Testing Grbl controller plugin. """

#pylint: disable=protected-access

from pygcode import Block, Line

import unittest
import loader  # pylint: disable=E0401,W0611
from definitions import ConnectionState, FlagState
from controllers.debug import DebugController


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


class TestControllerConnectionStates(unittest.TestCase):
    """ Connect and disconnect to controller. """

    def setUp(self) -> None:
        self.controller = DebugController()
        self.controller._time = MockTime()
        self.controller.connection_status = ConnectionState.CONNECTED
        self.controller.desired_connection_status = ConnectionState.CONNECTED

        self.assertEqual(len(self.controller.gcode), 0)

    def test_connect(self) -> None:
        """ Controller transitions to CONNECTED state after a delay. """
        self.controller.connection_status = ConnectionState.NOT_CONNECTED
        self.assertEqual(self.controller.desired_connection_status,
                         ConnectionState.CONNECTED)

        self.controller._time.return_values = [1000, 2000]
        self.controller.early_update()

        self.assertEqual(self.controller.connection_status,
                         ConnectionState.CONNECTING)
        self.assertFalse(self.controller.ready_for_data)

        self.controller._time.return_values = [3000, 4000]
        self.controller.early_update()

        self.assertEqual(self.controller.connection_status,
                         ConnectionState.CONNECTED)
        self.assertTrue(self.controller.ready_for_data)

    def test_disconnect(self) -> None:
        """ Controller transitions to NOT_CONNECTED state after a delay. """
        self.assertEqual(self.controller.connection_status, ConnectionState.CONNECTED)
        self.controller.desired_connection_status = ConnectionState.NOT_CONNECTED

        self.controller._time.return_values = [1000, 2000]
        self.controller.early_update()

        self.assertEqual(self.controller.connection_status,
                         ConnectionState.DISCONNECTING)
        self.assertFalse(self.controller.ready_for_data)

        self.controller._time.return_values = [3000, 4000]
        self.controller.early_update()

        self.assertEqual(self.controller.connection_status,
                         ConnectionState.NOT_CONNECTED)
        self.assertFalse(self.controller.ready_for_data)


class TestControllerSendData(unittest.TestCase):
    """ Send data to controller. """

    def setUp(self) -> None:
        self.controller = DebugController()
        self.controller._time = MockTime()
        self.controller.connection_status = ConnectionState.CONNECTED
        self.controller.desired_connection_status = ConnectionState.CONNECTED

        self.assertEqual(len(self.controller.gcode), 0)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})

        class MockCommand:  # pylint: disable=R0903: (too-few-public-methods)
            """ Container to pass input data to controller. """
            jog: FlagState = FlagState.UNSET
            gcode: Block = Line("G0 X10 Y20").block
        self.update = MockCommand()

    def test_incoming_gcode(self) -> None:
        """ Gcode gets passed on to the pygcode VM. """
        self.controller.ready_for_data = True
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        self.assertEqual(len(self.controller.gcode), 1)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})

        # Further calls to self.controller.update() should have no affect as
        # there is no new data.
        self.assertEqual(len(self.controller._queued_updates), 0)
        self.controller.update()
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})

    def test_incoming_gcode_g92(self) -> None:
        """ Local G92 implementation.
        G92: GCodeCoordSystemOffset is not handled by pygcode's VM so we manually
        compute the offset. """
        self.controller.ready_for_data = True
        self.update.gcode = Line("G92 X10 Y20").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        # G92 should have created a diff between machine_pos and work_pos.
        self.assertEqual(len(self.controller.gcode), 1)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})

        # Now move and observe diff between machine_pos and work_pos.
        self.controller.ready_for_data = True
        self.update.gcode = Line("G0 X10 Y20").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        self.assertEqual(len(self.controller.gcode), 2)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 20, "y": 40, "z": 0, "a": 0, "b": 0})

        # Further G92's work as expected.
        self.controller.ready_for_data = True
        self.update.gcode = Line("G92 X0 Y0").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        self.assertEqual(len(self.controller.gcode), 3)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})

        self.controller.ready_for_data = True
        self.update.gcode = Line("G0 X0 Y0").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        self.assertEqual(len(self.controller.gcode), 4)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": -10, "y": -20, "z": 0, "a": 0, "b": 0})

    def test_incoming_gcode_g92p1(self) -> None:
        """ Local G92.1 implementation.
        G92.1: GCodeResetCoordSystemOffset is not handled by pygcode's VM so we
        manually compute the offset. """

        # Use G92 to create a diff between machine_pos and work_pos.
        self.controller.ready_for_data = True
        self.update.gcode = Line("G92 X10 Y20").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        self.assertEqual(len(self.controller.gcode), 1)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 10, "y": 20, "z": 0, "a": 0, "b": 0})

        # Now G92.1
        self.controller.ready_for_data = True
        self.update.gcode = Line("G92.1").block
        self.controller._queued_updates.append(self.update)
        self.controller.update()

        # G92.1 should have reset the diff between machine_pos and work_pos.
        self.assertEqual(len(self.controller.gcode), 2)
        self.assertEqual(self.controller.state.machine_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})
        self.assertEqual(self.controller.state.work_pos,
                         {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0})

if __name__ == '__main__':
    unittest.main()
