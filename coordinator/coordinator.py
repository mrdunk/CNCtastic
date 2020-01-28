from typing import List, Dict, Any, Tuple, Deque, Optional
from collections import deque

from component import _ComponentBase
from definitions import FlagState, ConnectionState
from controllers._controllerBase import _ControllerBase

class Coordinator(_ComponentBase):
    """ Contains all system data.
    Handles polling all other components for new data and updating them as they
    request data. """

    def __init__(self, terminals: List, interfaces: List, controllers: List,
                 debug_show_events: bool = False) -> None:
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        super().__init__("__coordinator__")

        self.terminals: Dict = {terminal.label:terminal for terminal in terminals}
        self.interfaces: Dict = {interface.label:interface for interface in interfaces}
        self.controllers: Dict = {controller.label:controller for controller in controllers}
        self.debug_show_events = debug_show_events

        self.activeController = None

        self.activateController()
        
        self.allComponents = ( 
                [self] + 
                list(terminals) + 
                list(interfaces) + 
                list(controllers))
        self.terminalSpecificSetup()

        self.running = True

        self.event_subscriptions = {}
        # Change which controller is active in response to event.
        for controller in self.controllers:
            self.event_subscriptions["%s:active" % controller] = (
                    "_activeControllerOnEvent", controller)

    def terminalSpecificSetup(self) -> None:
        # Gather GUI layouts from all components.
        layouts = {}
        for component in self.allComponents:
            try:
                layouts[component.label] = component.gui_layout()   # type: ignore
            except AttributeError:
                # component does not have gui_layout property.
                pass

        # Activate terminals.
        for terminal in self.terminals.values():
            print("Terminal %s being activated: %s" % (terminal.label, terminal.active))
            if not terminal.active:
                continue

            if hasattr(terminal, "layout"):
                print("Configuring GUI: %s" % terminal.label)
                terminal.setup(layouts)
            else:
                terminal.setup()


    def _clearEvents(self) -> None:
        #if(self._eventQueue):
        #    print("Clearing event queue: ", self._eventQueue)
        self._eventQueue.clear()

    def _debugDisplayEvents(self) -> None:
        if not self.debug_show_events:
            return
        for event in self._eventQueue:
            print("*********", event)

    def activateController(self,
                           label: Optional[str]=None,
                           controller: Optional[_ControllerBase]=None) -> None:
        """ Set a specified controller as the active one.
        Args:
            label: If set, the active controller will be the one matching "label"
                   parameter.
            controller: If set, the active controller will be the one matching
                   this instance. If no matching instance is found, it will be
                   added as a candidate and activated.
        """
        def _activate(candidate: _ControllerBase) -> None:
            if self.activeController:
                self.activeController.active = False
            self.activeController = candidate

        def _onlyOneActive() -> None:
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

        if self.activeController and not controller:
            _onlyOneActive()
            return
        if (self.activeController and controller and
                self.activeController.label == controller.label):
            _onlyOneActive()
            return
        if self.activeController and self.activeController is controller:
            _onlyOneActive()
            return

        # Label was not specified as one of the input arguments.
        assert label is None, "Could not find controller matching '%s'" % label
        assert controller, "Controller not passed in as an argument."

        # This is a new controller.
        self.controllers[controller.label] = controller
        self.allComponents.append(controller)
        self.activeController = controller
        _onlyOneActive()

    def _activeControllerOnEvent(self, event_name: str, event_value: bool) -> None:
        """ Make whichever controller has it's "active" property set the active
            one. """

        eventControllerName, event_name = event_name.split(":", maxsplit=1)
        assert event_name == "active", "Unexpected event name: %s" % event_name

        if self.controllers[eventControllerName].active == event_value:
            # No change
            return

        print("New active controller: %s is %s" % (eventControllerName, event_value))

        assert eventControllerName in self.controllers, \
                "Event received from invalid controller."
        if event_value:
            for controller in self.controllers.values():
                controller.active = False
        self.controllers[eventControllerName].active = event_value

        # This will check only one controller has the active flag set
        # or assign the "debug" controller active if none are set.
        self.activateController()

        for controllerName, controller in self.controllers.items():
            self.publish_one_by_value("%s:active" % controllerName, controller.active)

    def _copyActiveControllerEvents(self) -> None:
        """ All controllers publish events under their own name. Subscribers
        are usually only interested in the active controller.
        Here we make copies of the active controller's events under the name
        "activeController:xxxx" to save working this out on every consumer."""
        assert self.activeController, "No active controller."

        acLabel = self.activeController.label
        tmpEventQueue = deque()
        for event_name, event_value in self._eventQueue:
            if not isinstance(event_name, str):
                continue
            if event_name.find(":") < 0:
                continue
            component, event = event_name.split(":", maxsplit=1)
            if component != acLabel:
                continue
            tmpEventQueue.append(("activeController:%s" % event, event_value))

        self._eventQueue.extend(tmpEventQueue)

    def updateComponents(self) -> bool:
        """ Iterate through all components, delivering and acting upon events. """
        for terminalName, terminal in self.terminals.items():
            if terminal.active:
                self.running = self.running and terminal.early_update()

        for component in self.interfaces.values():
            component.early_update()

        for controller in self.controllers.values():
            controller.early_update()

        # Publish all events.
        self.publish()
        for component in self.allComponents:
            component.publish()

        self._copyActiveControllerEvents()

        # Deliver all events to consumers.
        self.receive()
        for component in self.allComponents:
            component.receive()
        
        self._debugDisplayEvents()
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

    def close(self) -> None:
        for controller in self.controllers.values():
            controller.disconnect()
        for terminal in self.terminals.values():
            terminal.close()

