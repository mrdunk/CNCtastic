from typing import List, Dict
from collections import deque

from pygcode import block, Machine

from definitions import FlagState, State, Command, ConnectionState

class _CoreComponent:
    """ General methods required by all components. """

    # Mapping of event names to callback methods or property names.
    eventActions: Dict = {
            # "$COMPONENTNAME:$DESCRIPTION": ("$METHODNAME", None),
            # "$COMPONENTNAME:$DESCRIPTION": ("$METHODNAME", $DEFAULTVALUE),
            # "$COMPONENTNAME:$DESCRIPTION": ("$PROPERTYNAME", $DEFAULTVALUE)
            }

    def performEvent(self, events):
        """ Perform actions in response to specific events.
        Typically sets some variable in this class or executes a method there.
        Exact behaviour is configured in the self.eventActions Dict. """
        for key, value in events.items():
            if key in self.eventActions:
                if value is None:
                    assert self.eventActions[key][1] is not None, \
                            "No valid data being passed and no default configured."
                    # Use the value specified in self.eventActions.
                    value = self.eventActions[key][1]

                attr = getattr(self, self.eventActions[key][0])
                #print(self.label, key, value, self.eventActions[key])
                if callable(attr):
                    # Refers to a class method.
                    attr(value)
                else:
                    # Refers to a class variable.
                    setattr(self, self.eventActions[key][0], value)
    
    def exportToGui(self) -> Dict:
        """ Export values in this class to be consumed by GUI.
        Returns:
            A Dict where the key is the key of the GUI widget to be populated
            and the value is a member od this class. """
        raise NotImplementedError
        return {}

class Coordinator(_CoreComponent):
    """ Contains all system data.
    Handles polling all other components for new data and updating them as they
    request data. """

    def __init__(self, interfaces: List, controllers: List):
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        self.label = "__coordinator__"
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

    def exportToGui(self) -> Dict:
        """ Export values in this class to be consumed by GUI.
        Returns:
            A Dict where the key is the key of the GUI widget to be populated
            and the value is a member od this class. """
        return {
                "controllers": self.controllers.keys(),
                "confirmedSequence": self.state.confirmedSequence,
                "physical:feedRate": self.state.physical["feedRate"],
                "physical:toolNumber": self.state.physical["toolNumber"],
                "physical:spindleSpeed": self.state.physical["spindleSpeed"],
                "physical:coordinates:x": self.state.physical["coordinates"]["x"],
                "physical:coordinates:y": self.state.physical["coordinates"]["y"],
                "physical:coordinates:z": self.state.physical["coordinates"]["z"],
                "physical:coordinates:a": self.state.physical["coordinates"]["a"],
                "physical:coordinates:b": self.state.physical["coordinates"]["b"],
                "physical:halt": self.state.physical["halt"],
                "physical:pause": self.state.physical["pause"],
                "physical:alarm": self.state.physical["alarm"],
                }

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

        self.activeController.service()

        if not self.activeController.connectionStatus == ConnectionState.CONNECTED:
            return
        
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

