#!/usr/bin/env python3

""" Base infrastructure tests.
    Plug in components will be tested in separate test files. """

#pylint: disable=protected-access

import sys
import os
TESTDIR = os.path.dirname(__file__)
SRCDIR = '../'
sys.path.insert(0, os.path.abspath(os.path.join(TESTDIR, SRCDIR)))

import unittest
from coordinator.coordinator import Coordinator
from controllers.mockController import MockController
from interfaces.jog import JogWidget
from definitions import ConnectionState


class TestController(unittest.TestCase):
    """ Controllers base functionality. """
    def setUp(self):
        self.mock_controller = MockController()

    def test_initilise(self):
        """ Connect and disconnect the controller. """
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.UNKNOWN)
        self.assertFalse(self.mock_controller.ready_for_data)

        self.mock_controller.early_update()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.UNKNOWN)

        self.mock_controller.connect()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTING)
        self.assertFalse(self.mock_controller.ready_for_data)

        self.mock_controller.early_update()
        self.mock_controller.ready_for_data = True  # Will stay set while still connected.
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTED)
        self.assertTrue(self.mock_controller.ready_for_data)

        self.mock_controller.connect()
        self.mock_controller.early_update()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTED)
        self.assertTrue(self.mock_controller.ready_for_data)

        self.mock_controller.disconnect()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.DISCONNECTING)
        self.assertFalse(self.mock_controller.ready_for_data)

        self.mock_controller.early_update()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.NOT_CONNECTED)
        self.assertFalse(self.mock_controller.ready_for_data)

        self.mock_controller.disconnect()
        self.mock_controller.early_update()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.NOT_CONNECTED)

        self.mock_controller.connect()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTING)
        self.assertFalse(self.mock_controller.ready_for_data)

        self.mock_controller.early_update()
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTED)

    def test_valid_gcode_by_string(self):
        """ TODO """

    def test_valid_gcode_by_line(self):
        """ TODO """

    def test_disabled_not_reacts_to_event(self):
        """ TODO """

    def test_enabled_reacts_to_event(self):
        """ TODO """

class TestCoordinator(unittest.TestCase):
    """ Coordinator interaction with components. """

    def setUp(self):
        self.mock_widget = JogWidget()
        self.mock_controller = MockController()
        self.coordinator = Coordinator([], [self.mock_widget], [self.mock_controller])
        self.coordinator.active_controller = self.mock_controller
        self.coordinator.active_controller.connect()
        self.coordinator.update_components()  # Push events to subscribed targets.

        # Pacify linter.
        self.mock_controller1 = None
        self.mock_controller2 = None
        self.mock_controller3 = None
        self.mock_controller4 = None

    def tearDown(self):
        self.mock_widget._event_queue.clear()
        self.assertEqual(len(self.mock_controller._event_queue), 0)
        self.coordinator.close()

    def test_collection_name_is_label(self):
        """ The keys in the collections should match the component's label. """
        self.mock_controller1 = MockController("debug")
        self.mock_controller2 = MockController("owl")
        self.coordinator = Coordinator([], [], [self.mock_controller1, self.mock_controller2])

        self.assertIn(self.mock_controller1.label, self.coordinator.controllers)
        self.assertIn(self.mock_controller2.label, self.coordinator.controllers)

    def test_activate_controller_tiebreaker(self):
        """ The "debug" controller gets enabled if no others are eligible. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = False
        self.mock_controller2.active = False
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertTrue(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller3)

    def test_activate_controller_active_flag(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = False
        self.mock_controller2.active = True
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        self.assertFalse(self.mock_controller1.active)
        self.assertTrue(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller2)

    def test_activate_controller_multi_active_flag(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = True
        self.mock_controller2.active = True
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        self.assertTrue(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller1)

    def test_activate_controller_prefer_not_debug(self):
        """ The first controller with it's "active" flag set gets enabled but
        prefer one that isn't the debug one."""
        self.mock_controller1 = MockController("debug")
        self.mock_controller2 = MockController("owl")
        self.mock_controller3 = MockController("tiger")
        self.mock_controller1.active = True
        self.mock_controller2.active = False
        self.mock_controller3.active = True
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Not the first active in the list..
        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertTrue(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller3)

    def test_activate_controller_add_later(self):
        """ Add a new controller later. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = True
        self.mock_controller2.active = False
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Auto chose the active one.
        self.assertTrue(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller1)

        self.mock_controller4 = MockController("KingKong")
        self.mock_controller4.active = False
        self.coordinator.activate_controller(controller=self.mock_controller4)

        # The new one is now added and active.
        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertTrue(self.mock_controller4.active)
        self.assertIn(self.mock_controller4.label, self.coordinator.controllers)
        self.assertIn(self.mock_controller4, self.coordinator.all_components)
        self.assertEqual(self.coordinator.all_components.count(self.mock_controller4), 1)
        self.assertIs(self.coordinator.active_controller, self.mock_controller4)

    def test_activate_controller_by_instance(self):
        """ Enable a controller specified by instance. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = True
        self.mock_controller2.active = False
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Auto chose the active one.
        self.assertTrue(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller1)

        self.coordinator.activate_controller(controller=self.mock_controller2)

        # The specified one is now active.
        self.assertFalse(self.mock_controller1.active)
        self.assertTrue(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIn(self.mock_controller2.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.active_controller, self.mock_controller2)
        self.assertEqual(self.coordinator.all_components.count(self.mock_controller2), 1)

    def test_activate_controller_by_label(self):
        """ The controller with the specified label gets enabled. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = True
        self.mock_controller2.active = False
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Auto chose the active one.
        self.assertTrue(self.mock_controller1.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller1)

        self.coordinator.activate_controller(label="debug")

        # The specified one is now active.
        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertTrue(self.mock_controller3.active)
        self.assertIn(self.mock_controller3.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.active_controller, self.mock_controller3)

    def test_activate_controller_on_event_set(self):
        """ The "_active_controller_on_event" event handler changes active controller. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = False
        self.mock_controller2.active = False
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Default startup has "debug" controller active.
        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertTrue(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller3)

        # "_active_controller_on_event" changes the default controller.
        self.coordinator._active_controller_on_event("tiger:active", True)

        self.assertFalse(self.mock_controller1.active)
        self.assertTrue(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller2)

    def test_activate_controller_on_event_unset(self):
        """ The "_active_controller_on_event" event handler un-sets active controller,
        returning it to "debug". """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.mock_controller3 = MockController("debug")
        self.mock_controller1.active = False
        self.mock_controller2.active = True
        self.mock_controller3.active = False
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2, self.mock_controller3])

        # Default startup has "debug" controller active.
        self.assertFalse(self.mock_controller1.active)
        self.assertTrue(self.mock_controller2.active)
        self.assertFalse(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller2)

        # "_active_controller_on_event" un-sets the currently active.
        # The default controller ("debug") will be made the active.
        self.coordinator._active_controller_on_event("tiger:active", False)

        self.assertFalse(self.mock_controller1.active)
        self.assertFalse(self.mock_controller2.active)
        self.assertTrue(self.mock_controller3.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller3)

    def test_push_from_interface_to_controller(self):
        """ Data pushed as an event is processed by the controller. """
        def data_match(gcode, data):
            for section in gcode.gcodes:
                param_dict = section.get_param_dict()
                if section.word_letter == "G":
                    self.assertEqual(param_dict["X"], data["X"])
                    self.assertEqual(param_dict["Y"], data["Y"])
                elif section.word_letter == "F":
                    self.assertEqual(str(section), "F%s" % data["F"])

        self.assertIs(self.coordinator.active_controller, self.mock_controller)
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTED)
        # No data on mock_controller yet.
        self.assertEqual(len(self.mock_controller.gcode), 0)

        # Send data to controller.
        data = {"X": 10, "Y": 20, "F": 100}
        self.mock_widget.move_to(**data)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.

        self.assertEqual(len(self.mock_controller.gcode), 1)
        self.assertEqual(self.mock_controller.gcode[-1][0], "TRUE")
        data_match(self.mock_controller.gcode[-1][1], data)

        # Send more data to controller.
        data = {"X": 1.2345, "Y": -6.7889, "F": 1000}
        self.mock_widget.move_to(**data)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.

        self.assertEqual(len(self.mock_controller.gcode), 2)
        self.assertEqual(self.mock_controller.gcode[-1][0], "TRUE")
        data_match(self.mock_controller.gcode[-1][1], data)

    def test_swap_controllers(self):
        """ Push to one controller, set a different controller active, push there
        then revert and confirm original has correct state. """
        self.assertIs(self.coordinator.active_controller, self.mock_controller)
        self.assertEqual(self.mock_controller.connection_status, ConnectionState.CONNECTED)
        # No data on mock_controller yet.
        self.assertEqual(len(self.mock_controller.gcode), 0)

        # Send data to controller.
        self.mock_widget.move_to(x=10, y=20, f=100)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.
        self.mock_widget.move_to(x=50, y=100, f=100)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.

        self.assertEqual(len(self.mock_controller.gcode), 2)

        # Create new controller and make it active.
        self.mock_controller2 = MockController("owl")
        self.mock_controller2.connect()
        self.mock_controller2.early_update()  # Move from CONNECTING to CONNECTED
        self.coordinator.activate_controller(controller=self.mock_controller2)

        self.assertEqual(self.mock_controller2.connection_status, ConnectionState.CONNECTED)

        self.assertFalse(self.mock_controller.active)
        self.assertTrue(self.mock_controller2.active)
        self.assertIs(self.coordinator.active_controller, self.mock_controller2)

        # No data on mock_controller2 yet.
        self.assertEqual(len(self.mock_controller2.gcode), 0)

        # Push data to new controller.
        self.mock_widget.move_to(x=100, y=200, f=1000)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.

        # Has not changed data on old (inactive) controller.
        self.assertEqual(len(self.mock_controller.gcode), 2)
        # Has changed data on new (active) controller.
        self.assertEqual(len(self.mock_controller2.gcode), 1)

        # Back to original controller.
        self.coordinator.activate_controller(controller=self.mock_controller)

        # Push data to original controller.
        self.mock_widget.move_to(x=-1, y=-2, f=1)
        self.coordinator.update_components()  # Push event from mock_widget onto queue.
        self.coordinator.update_components()  # Push event from queue to mock_controller.

        # New data on old (active) controller.
        self.assertEqual(len(self.mock_controller.gcode), 3)
        # No change on new (inactive) controller.
        self.assertEqual(len(self.mock_controller2.gcode), 1)

    def test_component_names_match(self):
        """ Coordinator stores components keyed by their label. """
        self.mock_controller1 = MockController("owl")
        self.mock_controller2 = MockController("tiger")
        self.coordinator = Coordinator(
            [], [], [self.mock_controller1, self.mock_controller2])

        self.assertIn(self.mock_controller1.label, self.coordinator.controllers)


class TestEvents(unittest.TestCase):
    """ Test event handling.
    Note that this works without the input of the Controller but in the real
    world it would be used to clear the _event_queue between iterations. """

    def setUp(self):
        self.mock_controller = MockController()
        self.mock_widget = JogWidget()

        self.mock_widget._event_queue.clear()
        self.assertEqual(len(self.mock_controller._event_queue), 0)

    def tearDown(self):
        self.mock_widget._event_queue.clear()
        self.assertEqual(len(self.mock_controller._event_queue), 0)

    def test_publish_event_basic(self):
        """ Export some variables on one component, subscribe on another, then
        publish. """

        # Set up some dummy data to export on one component.
        self.mock_controller.testToExport = {}
        self.mock_controller.testToExport["bunny"] = "give me carrot"
        self.mock_controller.testToExport["onion"] = ["layer1", "layer2"]
        self.mock_controller.events_to_publish = {
            "testToExport1": "testToExport",
            "testToExport2": "testToExport.bunny",
            "testToExport3": "testToExport.onion",
            "testToExport4": "testToExport.onion.0",
            # Exporting an invalid member would assert.
            #"testToExport5": "testToExport.onion.invalidInt2",
            }

        # Set up some subscriptions.
        self.mock_widget.event_subscriptions = {
            "testToExport1": None,
            "testToExport2": None,
            "testToExport3": None,
            "testToExport4": None,
            # Its fine to subscribe to things that don't arrive.
            "missing": None,
            }

        # Now publish, populating the _event_queue.
        self.mock_controller.publish()
        self.assertEqual(len(self.mock_controller.events_to_publish),
                         len(self.mock_controller._event_queue))

        # Now call the receive on the other component making it read the _event_queue.
        self.mock_widget.receive()
        # Nothing delivered to the sender.
        self.assertEqual(0, len(self.mock_controller._delivered))
        # Full set delivered to the receiver.
        self.assertEqual(len(self.mock_controller.events_to_publish),
                         len(self.mock_widget._delivered))

    def test_publish_event_invalid_export_dict_args(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mock_controller.testToExport = {}
        self.mock_controller.testToExport["bunny"] = "give me carrot"
        self.mock_controller.events_to_publish = {
            "testToExport1": "testToExport.doggie",
            }

        # Now publish, populating the _event_queue.
        with self.assertRaises(AttributeError):
            self.mock_controller.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mock_controller._delivered))
        self.assertEqual(0, len(self.mock_widget._delivered))

    def test_publish_event_invalid_export_list_args(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mock_controller.testToExport = {}
        self.mock_controller.testToExport["onion"] = ["layer1", "layer2"]
        self.mock_controller.events_to_publish = {
            "testToExport1": "testToExport.onion.1invalidInt",
            }

        # Now publish, populating the _event_queue.
        with self.assertRaises(AttributeError):
            self.mock_controller.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mock_controller._delivered))
        self.assertEqual(0, len(self.mock_widget._delivered))

    def test_publish_event_missing_member_var(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mock_controller.testToExport = {}
        self.mock_controller.events_to_publish = {
            "testToExport1": "missingMember",
            }

        # Now publish, populating the _event_queue.
        with self.assertRaises(AttributeError):
            self.mock_controller.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mock_controller._delivered))
        self.assertEqual(0, len(self.mock_widget._delivered))

    def test_explicit_publish_by_value(self):
        """ TODO """

    def test_explicit_publish_by_name(self):
        """ TODO """


if __name__ == '__main__':
    unittest.main()
