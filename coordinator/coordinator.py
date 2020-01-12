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
        super().__init__("__coordinator__")

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

    def update(self) -> bool:
        """ Iterate through all other components and service all data transfer
        requests. """
        for terminalName, terminal in self.terminals.items():
            self.running = self.running and terminal.service()

        for component in self.interfaces.values():
            component.service()

        for controller in self.controllers.values():
            controller.service()
        #self.activeController.service()

        for component in self.allComponents:
            component.publish()

        for component in self.allComponents:
            component.receive()
        
        self._clearEvents()

        for component in self.allComponents:
            #if component._delivered:
            #    print(component.label, component._delivered)
            #else:
            #    print(component.label)

            component._processDeliveredEvents()
            component.processDeliveredEvents()
            component._delivered.clear()

        return self.running

    def close(self):
        for controller in self.controllers.values():
            controller.disconnect()
        for terminal in self.terminals.values():
            terminal.close()

