from typing import List
from collections import deque

from pygcode import block, Machine

from definitions import FlagState, State, Command
from controllers._controllerBase import ConnectionState


class Coordinator:
    """ Contains all system data.
    Handles polling all other components for new data and updating them as they
    request data. """

    def __init__(self, interfaces: List, controllers: List):
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        self.interfaces: Dict() = {}
        self.controllers: Dict() = {}
        for interface in interfaces:
            self.interfaces[interface.label] = interface
        for controller in controllers:
            self.controllers[controller.label] = controller
        self.activeController = None
        self.state: State
        self.gcode: deque = deque()

        self.activateController()

    def activateController(self, label=None, controller=None):
        def _activate(candidate):
            if self.activeController:
                self.activeController.active = False
            self.activeController = candidate
            self.state = candidate.state

        for controllerName, candidateController in self.controllers.items():
            if candidateController.label == "debug":
                _activate(candidateController)
                candidateController.active = False
        for controllerName, candidateController in self.controllers.items():
            if candidateController.active:
                _activate(candidateController)
                break
        for controllerName, candidateController in self.controllers.items():
            if candidateController.label == label:
                _activate(candidateController)
                break
        for controllerName, candidateController in self.controllers.items():
            if candidateController is controller:
                _activate(candidateController)
                break

        self.activeController.active = True

        if self.activeController and not controller:
            return

        assert not label, "Could not find controller matching '%s'" % label

        self.controllers[controller.label] = controller
        self.activeController = controller
        self.activeController.active = True
        self.state = self.activeController.state

    def update(self):
        """ Iterate through all other components and service all data transfer
        requests. """
        self._updateInterface()
        self._updateControler()

    def _updateInterface(self):
        for interfaceName, inpt in self.interfaces.items():
            if inpt.readyForPush:
                # TODO: This will make state mutable from the interface object.
                # Do we want this? Should we send a copy instead?
                inpt.push(self.state)
            if inpt.readyForPull:
                freshData: UpdateState = inpt.pull()

                self._parseGcode(freshData.gcode, freshData.jog == FlagState.TRUE)        
                if not freshData.halt == FlagState.UNSET:
                    self.state.halt = freshData.halt == FlagState.TRUE
                if not freshData.pause == FlagState.UNSET:
                    self.state.pause = freshData.pause == FlagState.TRUE

    def _updateControler(self):
        assert self.activeController, "No active controller."

        if not self.activeController.connectionStatus == ConnectionState.CONNECTED:
            return

        self.activeController.service()
        
        if self.activeController.readyForPush:
            command = Command()
            command.halt = self.state.halt
            command.pause = self.state.pause
            if self.gcode:
                command.gcode = self.gcode.popleft()
            self.activeController.push(command)

        if self.activeController.readyForPull:
            freshData = self.activeController.pull()
        
    def _parseGcode(self, gcodes: block.Block, jog: bool = False):
        if gcodes is None:
            return

        command = None
        for gcode in gcodes.gcodes:
            if gcode.word_key:
                command = gcode.word_key
                break
        if not self.activeController.isGcodeSupported(command):
            print("Gcode: %s not supported." % command)
            return

        self.state.vm.process_block(gcodes)
        if jog:
            self.gcode.append({"gcode": gcodes, "jog": True})
        else:
            self.gcode.append({"gcode": gcodes})

