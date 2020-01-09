import sys, os
testdir = os.path.dirname(__file__)
srcdir = '../'
sys.path.insert(0, os.path.abspath(os.path.join(testdir, srcdir)))

from collections import deque
import unittest
from pygcode import block, GCodeCublcSpline
from definitions import FlagState, Command, ConnectionState
from coordinator.coordinator import Coordinator
from interfaces.mockInterface import MockWidget
from controllers.mockController import MockController


class TestController(unittest.TestCase):
    def setUp(self):
        self.mockController = MockController()

    def test_initilise(self):
        """ Connect and disconnect the controller. """
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.UNKNOWN)
        self.assertFalse(self.mockController.readyForPush)

        self.mockController.service()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.UNKNOWN)

        self.mockController.connect()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTING)
        self.assertFalse(self.mockController.readyForPush)

        self.mockController.service()
        self.mockController.readyForPush = True  # Will stay set while still connected.
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTED)
        self.assertTrue(self.mockController.readyForPush)

        self.mockController.connect()
        self.mockController.service()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTED)
        self.assertTrue(self.mockController.readyForPush)

        self.mockController.disconnect()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.DISCONNECTING)
        self.assertFalse(self.mockController.readyForPush)

        self.mockController.service()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.NOT_CONNECTED)
        self.assertFalse(self.mockController.readyForPush)

        self.mockController.disconnect()
        self.mockController.service()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.NOT_CONNECTED)

        self.mockController.connect()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTING)
        self.assertFalse(self.mockController.readyForPush)

        self.mockController.service()
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTED)

    def test_validGcodeByString(self):
        """ """
        # TODO

    def test_validGcodeByLine(self):
        """ """
        # TODO

    def test_disabledNotReactsToEvent(self):
        """ 
        """
        # TODO

    def test_enabledReactsToEvent(self):
        """ 
        """
        # TODO

class TestCoordinator(unittest.TestCase):
    def setUp(self):
        self.mockWidget = MockWidget()
        self.mockController = MockController()
        self.coordinator = Coordinator([], [self.mockWidget], [self.mockController])
        self.coordinator.activeController = self.mockController
        self.coordinator.activeController.connect()
        self.coordinator.update()  # Push events to subscribed targets.

    def tearDown(self):
        self.mockWidget._eventQueue.clear()
        self.assertEqual(len(self.mockController._eventQueue), 0)
        self.coordinator.close()

    def test_collectionNameIsLabel(self):
        """ The keys in the collections should match the component's label. """
        self.mockController1 = MockController("debug")
        self.mockController2 = MockController("owl")
        self.coordinator = Coordinator([], [], [self.mockController1, self.mockController2])

        self.assertIn(self.mockController1.label, self.coordinator.controllers)
        self.assertIn(self.mockController2.label, self.coordinator.controllers)

    def test_activateControllerTiebreaker(self):
        """ The "debug" controller gets enabled if no others are eligible. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = False
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        self.assertFalse(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertTrue(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController3)

    def test_activateControllerActiveFlag(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = False
        self.mockController2.active = True
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        self.assertFalse(self.mockController1.active)
        self.assertTrue(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController2)

    def test_activateControllerMultiActiveFlag(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = True
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        self.assertTrue(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

    def test_activateControllerPreferNotDebug(self):
        """ The first controller with it's "active" flag set gets enabled but
        prefer one that isn't the debug one."""
        self.mockController1 = MockController("debug")
        self.mockController2 = MockController("owl")
        self.mockController3 = MockController("tiger")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = True
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        # Not the first active in the list..
        self.assertFalse(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertTrue(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController3)

    def test_activateControllerAddLater(self):
        """ Add a new controller later. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.mockController4 = MockController("KingKong")
        self.mockController4.active = False
        print(self.mockController4)
        self.coordinator.activateController(controller=self.mockController4)
        
        # The new one is now added and active.
        self.assertFalse(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertTrue(self.mockController4.active)
        self.assertIn(self.mockController4.label, self.coordinator.controllers)
        self.assertIn(self.mockController4, self.coordinator.allComponents)
        self.assertEqual(self.coordinator.allComponents.count(self.mockController4), 1)
        self.assertIs(self.coordinator.activeController, self.mockController4)

    def test_activateControllerByInstance(self):
        """ Enable a controller specified by instance. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.coordinator.activateController(controller=self.mockController2)
        
        # The specified one is now active.
        self.assertFalse(self.mockController1.active)
        self.assertTrue(self.mockController2.active)
        self.assertFalse(self.mockController3.active)
        self.assertIn(self.mockController2.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.activeController, self.mockController2)
        self.assertEqual(self.coordinator.allComponents.count(self.mockController2), 1)

    def test_activateControllerByLabel(self):
        """ The controller with the specified label gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.coordinator.activateController(label="debug")
        
        # The specified one is now active.
        self.assertFalse(self.mockController1.active)
        self.assertFalse(self.mockController2.active)
        self.assertTrue(self.mockController3.active)
        self.assertIn(self.mockController3.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.activeController, self.mockController3)

    def test_pushFromInterfaceToController(self):
        """ Data pushed as an event is processed by the controller. """
        def dataMatch(gcode, data):
            for section in gcode.gcodes:
                paramDict = section.get_param_dict()
                if section.word_letter == "G":
                    self.assertEqual(paramDict["X"], data["X"])
                    self.assertEqual(paramDict["Y"], data["Y"])
                elif section.word_letter == "F":
                    self.assertEqual(str(section), "F%s" % data["F"])

        self.assertIs(self.coordinator.activeController, self.mockController)
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTED)
        # No data on mockController yet.
        self.assertEqual(len(self.mockController.gcode), 0)

        # Send data to controller.
        data = {"X": 10, "Y": 20, "F": 100}
        self.mockWidget.moveTo(**data)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.

        self.assertEqual(len(self.mockController.gcode), 1)
        self.assertEqual(self.mockController.gcode[-1][0], "jog")
        dataMatch(self.mockController.gcode[-1][1], data)

        # Send more data to controller.
        data = {"X": 1.2345, "Y": -6.7889, "F": 1000}
        self.mockWidget.moveTo(**data)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.

        self.assertEqual(len(self.mockController.gcode), 2)
        self.assertEqual(self.mockController.gcode[-1][0], "jog")
        dataMatch(self.mockController.gcode[-1][1], data)

    def test_swapControllers(self):
        """ Push to one controller, set a different controller active, push there
        then revert and confirm original has correct state. """
        self.assertIs(self.coordinator.activeController, self.mockController)
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.CONNECTED)
        # No data on mockController yet.
        self.assertEqual(len(self.mockController.gcode), 0)

        # Send data to controller.
        self.mockWidget.moveTo(x=10, y=20, f=100)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.
        self.mockWidget.moveTo(x=50, y=100, f=100)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.

        self.assertEqual(len(self.mockController.gcode), 2)
        
        # Create new controller and make it active.
        self.mockController2 = MockController("owl")
        self.mockController2.connect()
        self.mockController2.service()  # Move from CONNECTING to CONNECTED
        self.coordinator.activateController(controller=self.mockController2)

        self.assertEqual(self.mockController2.connectionStatus, ConnectionState.CONNECTED)

        self.assertFalse(self.mockController.active)
        self.assertTrue(self.mockController2.active)
        self.assertIs(self.coordinator.activeController, self.mockController2)

        # No data on mockController2 yet.
        self.assertEqual(len(self.mockController2.gcode), 0)

        # Push data to new controller.
        self.mockWidget.moveTo(x=100, y=200, f=1000)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.

        # Has not changed data on old (inactive) controller.
        self.assertEqual(len(self.mockController.gcode), 2)
        # Has changed data on new (active) controller.
        self.assertEqual(len(self.mockController2.gcode), 1)

        # Back to original controller.
        self.coordinator.activateController(controller=self.mockController)

        # Push data to original controller.
        self.mockWidget.moveTo(x=-1, y=-2, f=1)
        self.coordinator.update()  # Push event from mockWidget onto queue.
        self.coordinator.update()  # Push event from queue to mockController.

        # New data on old (active) controller.
        self.assertEqual(len(self.mockController.gcode), 3)
        # No change on new (inactive) controller.
        self.assertEqual(len(self.mockController2.gcode), 1)

    def test_componentNamesMatch(self):
        """ Coordinator stores components keyed by their label. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.coordinator = Coordinator([], [],
                [self.mockController1, self.mockController2])

        self.assertIn(self.mockController1.label, self.coordinator.controllers)


class TestEvents(unittest.TestCase):
    """ Test event handling.
    Note that this works without the input of the Controller but in the real
    world it would be used to clear the _eventQueue between iterations. """

    def setUp(self):
        self.mockController = MockController()
        self.mockWidget = MockWidget()

        self.mockWidget._eventQueue.clear()
        self.assertEqual(len(self.mockController._eventQueue), 0)

    def tearDown(self):
        self.mockWidget._eventQueue.clear()
        self.assertEqual(len(self.mockController._eventQueue), 0)

    def test_publishEventBasic(self):
        """ Export some variables on one component, subscribe on another, then
        publish. """

        # Set up some dummy data to export on one component.
        self.mockController.testToExport = {}
        self.mockController.testToExport["bunny"] = "give me carrot"
        self.mockController.testToExport["onion"] = ["layer1", "layer2"]
        self.mockController.exported = {
                "testToExport1": "testToExport",
                "testToExport2": "testToExport.bunny",
                "testToExport3": "testToExport.onion",
                "testToExport4": "testToExport.onion.0",
                # Exporting an invalid member would assert.
                #"testToExport5": "testToExport.onion.invalidInt2",
                }
        
        # Set up some subscriptions.
        self.mockWidget._subscriptions = {
                "testToExport1": None,
                "testToExport2": None,
                "testToExport3": None,
                "testToExport4": None,
                # Its fine to subscribe to things that don't arrive.
                "missing": None,
                }

        # Now publish, populating the _eventQueue.
        self.mockController.publish()
        self.assertEqual(len(self.mockController.exported),
                         len(self.mockController._eventQueue))

        # Now call the receive on the other component making it read the _eventQueue.
        self.mockWidget.receive()
        # Nothing delivered to the sender.
        self.assertEqual(0, len(self.mockController._delivered))
        # Full set delivered to the receiver.
        self.assertEqual(len(self.mockController.exported),
                         len(self.mockWidget._delivered))

    def test_publishEventInvalidExportDictArgs(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mockController.testToExport = {}
        self.mockController.testToExport["bunny"] = "give me carrot"
        self.mockController.exported = {
                "testToExport1": "testToExport.doggie",
                }
        
        # Now publish, populating the _eventQueue.
        with self.assertRaises(AttributeError):
            self.mockController.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mockController._delivered))
        self.assertEqual(0, len(self.mockWidget._delivered))

    def test_publishEventInvalidExportListArgs(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mockController.testToExport = {}
        self.mockController.testToExport["onion"] = ["layer1", "layer2"]
        self.mockController.exported = {
                "testToExport1": "testToExport.onion.1invalidInt",
                }
        
        # Now publish, populating the _eventQueue.
        with self.assertRaises(AttributeError):
            self.mockController.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mockController._delivered))
        self.assertEqual(0, len(self.mockWidget._delivered))

    def test_publishEventMissingMemberVar(self):
        """ Export some variables which are incorrectly named. """

        # Set up some dummy data to export on one component.
        self.mockController.testToExport = {}
        self.mockController.exported = {
                "testToExport1": "missingMember",
                }
        
        # Now publish, populating the _eventQueue.
        with self.assertRaises(AttributeError):
            self.mockController.publish()
        # Nothing delivered anywhere.
        self.assertEqual(0, len(self.mockController._delivered))
        self.assertEqual(0, len(self.mockWidget._delivered))

    def test_explicitPublishByValue(self):
        """ """
        pass

    def test_explicitPublishByName(self):
        """ """
        pass


if __name__ == '__main__':
    unittest.main()
