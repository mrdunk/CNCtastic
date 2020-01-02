import sys, os
testdir = os.path.dirname(__file__)
srcdir = '../'
sys.path.insert(0, os.path.abspath(os.path.join(testdir, srcdir)))

import unittest
from pygcode import block, GCodeCublcSpline
from definitions import FlagState, Command
from coordinator.coordinator import Coordinator
from interfaces.mockInterface import MockWidget
from controllers.mockController import MockController
from interfaces._interfaceBase import InterfaceState
from controllers._controllerBase import ConnectionState


class TestCoordinatorInterfacesPull(unittest.TestCase):
    def setUp(self):
        self.mockWidget = MockWidget()
        self.mockController = MockController()
        self.coordinator = Coordinator([self.mockWidget], [self.mockController])
        self.coordinator.activeController = self.mockController

        #self.assertDictEqual( self.coordinator.state.vm.pos.values,
        #                      {"X": 0, "Y": 0, "Z": 0})
        #self.assertFalse(self.coordinator.state.halt)
        #self.assertFalse(self.coordinator.state.pause)

    def test_pullCalledOnlyWhenFlagSet(self):
        """ Verify interface's "pull" method is called when it's "readyForPull" flag
        is set. """
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # Check "pull" method was not actually called as "readyForPull" flag was
        # not set.
        self.assertNotIn("pull", self.mockWidget.logCallData)

        # Set "readyForPull" flag indicating there is data to read.
        self.mockWidget.readyForPull = True
        # Poll mockWidget a few times.
        self.coordinator._updateInterface()
        self.coordinator._updateInterface()
        self.coordinator._updateInterface()

        # "pull" method was called once this time as the "readyForPull" flag is
        # reset between calls.
        self.assertIn("pull", self.mockWidget.logCallData)
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 1)
    
        # No change in the coordinator state though as the received data was not populated.
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 0, "Y": 0, "Z": 0})
        self.assertFalse(self.coordinator.state.halt)
        self.assertFalse(self.coordinator.state.pause)
        self.assertEqual(len(self.coordinator.gcode), 0)

    def test_pullUpdatesPosition(self):
        """ Have the interface set the position of the coordinator's state. """
        # No "pull" calls on the interface object yet.
        self.assertNotIn("pull", self.mockWidget.logCallData)

        # Set some data to pull from the inpt.
        self.mockWidget.moveTo(**{"x": 10, "y": 20.02, "z": -123.4})
        self.mockWidget._updatedData.pause = FlagState.TRUE
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # "pull" was called and the coordinator state was updated.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 1)
        self.assertDictEqual(self.coordinator.state.vm.pos.values,
                             {"X": 10, "Y": 20.02, "Z": -123.4})
        self.assertEqual(len(self.coordinator.gcode), 1)
        self.assertFalse(self.coordinator.state.halt)
        self.assertTrue(self.coordinator.state.pause)

    def test_pullUpdatesPositionRelative(self):
        """ Have the interface set the position of the coordinator's state. """
        # No "pull" calls on the interface object yet.
        self.assertNotIn("pull", self.mockWidget.logCallData)

        # Starting position.
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 0, "Y": 0, "Z": 0})

        # Set incremental distance.
        self.mockWidget.absoluteDistanceMode(command="G91")
        
        # Set some data to pull from the inpt.
        self.mockWidget.moveTo(**{"x": 10, "y": 20.02, "z": -123.4})
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # "pull" was called and the coordinator state was updated.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 1)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 10, "Y": 20.02, "Z": -123.4})

        # Only a single block of gcode despite absoluteDistanceMode() and moveTo()
        # as there was only a single _updateInterface() they both are in the same block.
        self.assertEqual(len(self.coordinator.gcode), 1)

        # Set some data to pull from the inpt.
        self.mockWidget.moveTo(**{"x": 1000})
        self.mockWidget.moveTo(**{"y": 1000})
        self.mockWidget.moveTo(**{"y": 1000})
        self.mockWidget.moveTo(command="G00", **{"y": 1000, "f": 4000})
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # "pull" was called and the coordinator state was updated.
        # Note that the move was added to the previous position.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 2)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 1010, "Y": 3020.02, "Z": -123.4})
        # All the above moveTo() get combined in a single gcode block.
        self.assertEqual(len(self.coordinator.gcode), 2)

    def test_pullUpdatesPositionNonStandard(self):
        """ Have the interface set the position of the coordinator's state using an
        alternative Move type. """
        # No "pull" calls on the interface object yet.
        self.assertNotIn("pull", self.mockWidget.logCallData)

        # Set some data to pull from the inpt.
        self.mockWidget.moveTo(command="G00", **{"x": 10, "y": -20.02, "z": 0.0})
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # "pull" was called and the coordinator state was updated.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 1)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 10, "Y": -20.02, "Z": 0})
        self.assertEqual(len(self.coordinator.gcode), 1)

        # Set the flag promising new data but the buffer has been cleared so
        # "pull" gets called but nothing else interesting happens.
        self.mockWidget.readyForPull = True
        self.coordinator._updateInterface()
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 2)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 10, "Y": -20.02, "Z": 0})
        self.assertEqual(len(self.coordinator.gcode), 1)

        # Set some data to pull from the inpt.
        # When 2 commands override each other, the result should be whichever comes last.
        self.mockWidget.moveTo(command="G00", **{"x": 1, "f": 2})
        self.mockWidget.moveTo(command="G00", **{"x": 1000, "f": 200})
        self.coordinator._updateInterface()

        # and it is added to the final position.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 3)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 1000, "Y": -20.02, "Z": 0})
        self.assertEqual(len(self.coordinator.gcode), 2)

    def test_pullUpdatesUnsuportedMotionMode(self):
        """ The controller keeps a list of which Gcode it supports and silently
        ignores an unsupported commands. """
        # No "pull" calls on the interface object yet.
        self.assertNotIn("pull", self.mockWidget.logCallData)

        # Use an Motion Mode that is not supported by the controller.
        # Hack the interface so it doesn't catch the unsupported Mode.
        self.mockWidget._updatedData.gcode = block.Block()
        self.mockWidget._updatedData.gcode.gcodes.append(GCodeCublcSpline(x=10, y=20))
        self.mockWidget.readyForPull = True
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # "pull" was called but no change in state due to unsupported gcode.
        self.assertEqual(len(self.mockWidget.logCallData["pull"]), 1)
        self.assertDictEqual( self.coordinator.state.vm.pos.values,
                              {"X": 0, "Y": 0, "Z": 0})
        self.assertEqual(len(self.coordinator.gcode), 0)


class TestCoordinatorInterfacesPush(unittest.TestCase):
    def setUp(self):
        self.mockWidget = MockWidget()
        self.mockController = MockController()
        self.coordinator = Coordinator([self.mockWidget], [self.mockController])
        self.coordinator.activeController = self.mockController

        self.assertDictEqual(self.coordinator.state.vm.pos.values,
                             {"X": 0, "Y": 0, "Z": 0})
        self.assertFalse(self.coordinator.state.halt)
        self.assertFalse(self.coordinator.state.pause)

    def test_pushIntitialisesInterface(self):
        self.assertIsNone(self.mockWidget.state)
        self.assertEqual(self.mockWidget.status, InterfaceState.UNKNOWN)

        self.mockWidget.connect()
        self.assertEqual(self.mockWidget.status, InterfaceState.STALE_DATA)
        self.assertNotIn("push", self.mockWidget.logCallData)

        # Poll mockWidget.
        self.coordinator._updateInterface()
        # No change because readyForPush flag was not set.
        self.assertEqual(self.mockWidget.status, InterfaceState.STALE_DATA)
        self.assertNotIn("push", self.mockWidget.logCallData)

        self.mockWidget.readyForPush = True
        # Poll mockWidget.
        self.coordinator._updateInterface()
        # Interface correctly updated.
        self.assertEqual(self.mockWidget.status, InterfaceState.UP_TO_DATE)
        self.assertEqual(len(self.mockWidget.logCallData["push"]), 1)
        self.assertIsNotNone(self.mockWidget.state)

    def test_pushUpdatesInterfaceState(self):
        self.mockWidget.connect()
        self.mockWidget.readyForPush = True
        # Poll mockWidget.
        self.coordinator._updateInterface()
        # Interface correctly updated.
        self.assertEqual(self.mockWidget.status, InterfaceState.UP_TO_DATE)
        self.assertEqual(len(self.mockWidget.logCallData["push"]), 1)
        self.assertIsNotNone(self.mockWidget.state)

        self.assertDictEqual(self.mockWidget.state.vm.pos.values,
                             {"X": 0, "Y": 0, "Z": 0})

        # Force a movment.
        self.mockWidget.moveTo(command="G00", **{"x": 10, "y": -20.02, "z": 0.0})
        # Change a flag.
        self.coordinator.state.pause = True
        # Poll mockWidget.
        self.coordinator._updateInterface()

        # Interface knows about changes before ._updateInterface() because it
        # shares a single instance of the state object with the coordinator.
        self.assertDictEqual(self.mockWidget.state.vm.pos.values,
                             {"X": 10, "Y": -20.02, "Z": 0})
        self.assertTrue(self.mockWidget.state.pause)

        # Because self.mockWidget.state remains up to date without further
        # self.mockWidget.push calls,
        # further polls of mockWidget don't do anything because the readyForPush
        # flag has been disabled.
        self.coordinator._updateInterface()
        self.assertEqual(len(self.mockWidget.logCallData["push"]), 1)


class TestController(unittest.TestCase):
    def setUp(self):
        self.mockController = MockController()

    def test_initilise(self):
        """ Connect and disconnect the controller. """
        self.assertEqual(self.mockController.connectionStatus, ConnectionState.UNKNOWN)
        self.assertFalse(self.mockController.readyForPush)
        self.assertFalse(self.mockController.readyForPull)

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

    def test_pushPullDataFlow(self):
        """ The MockController (and the DebugController it inherits from) will
        reply with the sequence number it was last sent. """
        self.mockController.connectionStatus = ConnectionState.CONNECTED
        data = Command()
        data.gcode = {"elephant": "Phwawww"}

        self.mockController.readyForPush = True
        self.mockController.push(data)

        self.mockController.readyForPull = True
        response = self.mockController.pull()
        self.assertEqual(data.sequence, response.sequence)

        # Does not change until a new Command is sent.
        self.mockController.readyForPull = True
        response = self.mockController.pull()
        self.assertEqual(data.sequence, response.sequence)

    def test_activateControllerTiebreaker(self):
        """ The "debug" controller gets enabled if no others are eligible. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = False
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

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
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        self.assertTrue(self.mockController2.active)
        self.assertIs(self.coordinator.activeController, self.mockController2)

    def test_activateControllerMultiActiveFlag(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = True
        self.mockController3.active = False
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        self.assertTrue(self.mockController1.active)
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
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        # Not the first active in the list..
        self.assertTrue(self.mockController3.active)
        self.assertIs(self.coordinator.activeController, self.mockController3)

    def test_activateControllerAddLater(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.mockController4 = MockController("KingKong")
        self.mockController4.active = False
        self.coordinator.activateController(controller=self.mockController4)
        
        # The new one is now added and active.
        self.assertTrue(self.mockController4.active)
        self.assertIn(self.mockController4.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.activeController, self.mockController4)

    def test_activateControllerByInstance(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.coordinator.activateController(controller=self.mockController2)
        
        # The specified one is now active.
        self.assertTrue(self.mockController2.active)
        self.assertIn(self.mockController2.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.activeController, self.mockController2)

    def test_activateControllerByInstance(self):
        """ The first controller with it's "active" flag set gets enabled. """
        self.mockController1 = MockController("owl")
        self.mockController2 = MockController("tiger")
        self.mockController3 = MockController("debug")
        self.mockController1.active = True
        self.mockController2.active = False
        self.mockController3.active = False
        self.coordinator = Coordinator([],
                [self.mockController1, self.mockController2, self.mockController3])

        # Auto chose the active one.
        self.assertTrue(self.mockController1.active)
        self.assertIs(self.coordinator.activeController, self.mockController1)

        self.coordinator.activateController(label="debug")
        
        # The specified one is now active.
        self.assertTrue(self.mockController3.active)
        self.assertIn(self.mockController3.label, self.coordinator.controllers)
        self.assertIs(self.coordinator.activeController, self.mockController3)


class TestCoordinatorControllerPush(unittest.TestCase):
    def setUp(self):
        self.mockWidget = MockWidget()
        self.mockController = MockController()
        self.coordinator = Coordinator([self.mockWidget], [self.mockController])
        self.coordinator.activeController = self.mockController
        self.coordinator.activeController.connect()
        self.coordinator.activeController.service()

    def test_controllerPush(self):
        """ A push to the controller sends the Coordinator's flags and a gcode
        dict from the buffer. """
        self.assertFalse(self.coordinator.state.halt)
        self.assertFalse(self.coordinator.state.pause)

        # Set up the Coordinator
        self.coordinator.state.halt = False
        self.coordinator.state.pause = True
        gcode = {"duck": "quack"}
        self.coordinator.gcode.append(gcode)

        # Do the push.
        self.mockController.readyForPush = True
        self.mockController.readyForPull = False
        self.coordinator._updateControler()

        self.assertEqual(len(self.mockController.logCallData["push"]), 1)
        self.assertEqual(len(self.mockController._sequences), 1)
        self.assertFalse(self.mockController._sequences[0].halt)
        self.assertTrue(self.mockController._sequences[0].pause)
        self.assertIs(self.mockController._sequences[0].gcode, gcode)
        
        # Do the same push but with an empty gcode buffer this time.
        self.mockController.readyForPush = True
        self.mockController.readyForPull = False
        self.coordinator._updateControler()
       
        self.assertEqual(len(self.mockController.logCallData["push"]), 2)
        self.assertEqual(len(self.mockController._sequences), 2)
        self.assertFalse(self.mockController._sequences[1].halt)
        self.assertTrue(self.mockController._sequences[1].pause)
        self.assertIsNone(self.mockController._sequences[1].gcode)

    def test_swapControllers(self):
        """ A push to the controller sends the Coordinator's flags and a gcode
        dict from the buffer. """
        self.assertFalse(self.coordinator.state.halt)
        self.assertFalse(self.coordinator.state.pause)

        # Set up the Coordinator
        self.coordinator.state.halt = False
        self.coordinator.state.pause = True
        gcode = {"duck": "quack"}
        self.coordinator.gcode.append(gcode)

        # Do the push.
        self.mockController.readyForPush = True
        self.mockController.readyForPull = False
        self.coordinator._updateControler()

        self.assertEqual(len(self.mockController.logCallData["push"]), 1)
        self.assertEqual(len(self.mockController._sequences), 1)
        self.assertFalse(self.mockController._sequences[0].halt)
        self.assertTrue(self.mockController._sequences[0].pause)
        self.assertIs(self.mockController._sequences[0].gcode, gcode)

        # Change to a different controller.
        mockController2 = MockController("trout")
        self.coordinator.activateController(controller=mockController2)

        # This one has had no data pushed to it yet.
        self.assertEqual(len(mockController2._sequences), 0)

        # Back to the original controller.
        self.coordinator.activateController(controller=self.mockController)

        # It has it's original state.
        self.assertEqual(len(self.mockController.logCallData["push"]), 1)
        self.assertEqual(len(self.mockController._sequences), 1)
        self.assertFalse(self.mockController._sequences[0].halt)
        self.assertTrue(self.mockController._sequences[0].pause)
        self.assertIs(self.mockController._sequences[0].gcode, gcode)



if __name__ == '__main__':
    unittest.main()
