from typing import List, Dict, Any, Tuple, Deque
from collections import deque

from pygcode import block, Machine

from component import _ComponentBase
from definitions import FlagState, Command, ConnectionState

class Coordinator(_ComponentBase):
    """ Contains all system data.
    Handles polling all other components for new data and updating them as they
    request data. """

    def __init__(self, terminals: List, interfaces: List, controllers: List):
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        self.terminals: Dict() = {terminal.label:terminal for terminal in terminals}
        self.interfaces: Dict() = {interface.label:interface for interface in interfaces}
        self.controllers: Dict() = {controller.label:controller for controller in controllers}

        self.activeController = None
        self.gcode: deque = deque()

        self.activateController()
        
        self.allComponents = ( 
                [self] + 
                list(terminals) + 
                list(interfaces) + 
                list(controllers))
        self.terminalSpecificSetup()

        self.running = True

        self.eventActions = {}
        for controller in self.controllers:
            self.eventActions["%s:active" % controller] = ("_changeActiveController", controller)

        super().__init__("__coordinator__")

    def _changeActiveController(self, eventName, eventValue):
        eventValue = bool(eventValue)

        eventControllerName = eventName.split(":")[0]

        if self.controllers[eventControllerName].active == eventValue:
            # No change
            return

        print(self._delivered)
        print("New active controller: %s is %s" % (eventControllerName, eventValue))

        assert eventControllerName in self.controllers, "Event received from invalid controller."
        if eventValue:
            for controller in self.controllers.values():
                controller.active = False
        self.controllers[eventControllerName].active = eventValue

        # This will check only one controller has the active flag set
        # or assign the "debug" controller active if none are set.
        self.activateController()

        for controllerName, controller in self.controllers.items():
            self.publishOneByValue("%s:active" % controllerName, controller.active)

    def terminalSpecificSetup(self):
        # Gather GUI layouts from all components.
        layouts = {}
        for component in self.allComponents:
            if hasattr(component, "guiLayout"):
                layouts[component.label] = component.guiLayout()

        # Activate terminals.
        for terminal in self.terminals.values():
            print("Terminal %s being activated: %s" % (terminal.label, terminal.activateNow))
            if not terminal.activateNow:
                continue

            if hasattr(terminal, "layout"):
                print("Configuring GUI: %s" % terminal.label)
                terminal.setup(layouts)
            else:
                terminal.setup()


    def _clearEvents(self):
        #if(self._eventQueue):
        #    print("Clearing event queue: ", self._eventQueue)
        self._eventQueue.clear()

    def activateController(self, label=None, controller=None):
        """ Set a controller as the active one.
        Args:
            label: If set, the active controller will be the one matching "label"
                   parameter.
            controller: If set, the active controller will be the one matching
                   this instance. If no matching instance is found, it will be
                   added as a candidate and activated.
        """
        def _activate(candidate):
            if self.activeController:
                self.activeController.active = False
            self.activeController = candidate

        def _onlyOneActive():
            assert self.activeController, "No active controller set."
            for controllerName, candidateController in self.controllers.items():
                if candidateController is self.activeController:
                    candidateController.active = True
                else:
                    candidateController.active = False

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
        if not self.activeController and not controller:
            # Don't have an self.activeController yet.
            # Let's just take the first.
            self.activeController = list(self.controllers.values())[0]

        if((self.activeController and not controller) or
                (self.activeController.label == controller.label) or
                (self.activeController is controller)):
            _onlyOneActive()
            return

        assert not label, "Could not find controller matching '%s'" % label

        # This is a new controller.
        self.controllers[controller.label] = controller
        self.allComponents.append(controller)
        self.activeController = controller
        _onlyOneActive()

    def updateComponents(self) -> bool:
        """ Iterate through all other components and service all data transfer
        requests. """
        for terminalName, terminal in self.terminals.items():
            self.running = self.running and terminal.earlyUpdate()

        for component in self.interfaces.values():
            component.earlyUpdate()

        for controller in self.controllers.values():
            controller.earlyUpdate()
        #self.activeController.earlyUpdate()

        self.publish()
        for component in self.allComponents:
            component.publish()

        self.receive()
        for component in self.allComponents:
            component.receive()
        
        self._clearEvents()

        self._update()
        self._delivered.clear()
        for component in self.allComponents:
            #if component._delivered:
            #    print(component.label, component._delivered)
            #else:
            #    print(component.label)

            component._update()
            component.update()
            component._delivered.clear()

        return self.running

    def close(self):
        for controller in self.controllers.values():
            controller.disconnect()
        for terminal in self.terminals.values():
            terminal.close()

