from typing import List, Dict, Any, Tuple, Deque
from collections import deque

from pygcode import block, Machine

from component import _ComponentBase
from definitions import FlagState, State, Command, ConnectionState

class Coordinator(_ComponentBase):
    """ Contains all system data.
    Handles polling all other components for new data and updating them as they
    request data. """

    def __init__(self, terminals: Dict, interfaces: Dict, controllers: Dict):
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        super().__init__("__coordinator__")

        self.terminals: Dict() = terminals
        self.interfaces: Dict() = interfaces
        self.controllers: Dict() = controllers

        self.activeController = None
        self.gcode: deque = deque()

        self.activateController()
        
        self.allComponents = ( 
                [self] + 
                list(terminals.values()) + 
                list(interfaces.values()) + 
                list(controllers.values()))
        self.guiSpecificSetup()

        self.running = True

    def guiSpecificSetup(self):
        needsLayout = []
        for terminal in self.terminals.values():
            if hasattr(terminal, "layout"):
                print("Configuring GUI: %s" % terminal.label)
                needsLayout.append(terminal)
        if not needsLayout:
            # No plugins care about GUI layout information.
            return

        layouts = {}
        for component in self.allComponents:
            if hasattr(component, "guiLayout"):
                layouts[component.label] = component.guiLayout()
        for component in needsLayout:
            component.setup(layouts)


    def _clearEvents(self):
        #if(self._eventQueue):
        #    print("Clearing event queue: ", self._eventQueue)
        self._eventQueue.clear()

    def activateController(self, label=None, controller=None):
        def _activate(candidate):
            if self.activeController:
                self.activeController.active = False
            self.activeController = candidate

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

    def update(self) -> bool:
        """ Iterate through all other components and service all data transfer
        requests. """
        for terminalName, terminal in self.terminals.items():
            self.running = self.running and terminal.service()

        for component in self.interfaces.values():
            component.service()

        self.activeController.service()

        for component in self.allComponents:
            component.publish()

        for component in self.allComponents:
            component.receive()
        
        self._clearEvents()

        for component in self.allComponents:
            #if component._delivered:
            #    print(component.label, component._delivered)

            component._processDeliveredEvents()
            component.processDeliveredEvents()
            component._delivered.clear()

        return self.running

    def close(self):
        for controller in self.controllers.values():
            controller.disconnect()
        for terminal in self.terminals.values():
            terminal.close()

