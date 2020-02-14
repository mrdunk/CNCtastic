""" Coordinator handles interactions between components.
Coordinator polls all components for published events and delivers them to
subscribers. """


from typing import List, Dict, Optional, Deque, Tuple, Any
from collections import deque

from component import _ComponentBase
from terminals._terminal_base import _TerminalBase
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase

class Coordinator(_ComponentBase):
    """ Coordinator handles interactions between components.
    Coordinator polls all components for published events and delivers them to
    subscribers. """

    def __init__(self,
                 terminals: List[_TerminalBase],
                 interfaces: List[_InterfaceBase],
                 controllers: List[_ControllerBase],
                 debug_show_events: bool = False) -> None:
        """
        Args:
            interfaces: A list of objects deriving from the _InterfaceBase class.
            controllers: A list of objects deriving from the _ControllerBase class.
        """
        super().__init__("__coordinator__")

        self.terminals: Dict[str, _TerminalBase] = \
                {terminal.label:terminal for terminal in terminals}
        self.interfaces: Dict[str, _InterfaceBase] = \
                {interface.label:interface for interface in interfaces}
        self.controllers: Dict[str, _ControllerBase] = \
                {controller.label:controller for controller in controllers}
        self.debug_show_events = debug_show_events

        self.active_controller: Optional[_ControllerBase] = None

        self.activate_controller()

        self.all_components: List[_ComponentBase] = [self]
        self.all_components += list(terminals)
        self.all_components += list(interfaces)
        self.all_components += list(controllers)

        self.terminal_specific_setup()

        self.running = True

        self.event_subscriptions = {}
        # Change which controller is active in response to event.
        for controller in self.controllers:
            self.event_subscriptions["%s:active" % controller] = (
                "_active_controller_on_event", controller)

    def terminal_specific_setup(self) -> None:
        """ Do configuration that was not possible before all other components
        were instantiated. """
        # Gather GUI layouts from all components.
        layouts = {}
        for component in self.all_components:
            try:
                layouts[component.label] = component.gui_layout()   # type: ignore
            except AttributeError:
                # component does not have gui_layout property.
                pass

        # Activate terminals.
        for terminal in self.terminals.values():
            print("Terminal %s of type %s is being activated." %
                  (terminal.label, terminal.get_classname()))

            if hasattr(terminal, "layout"):
                print("Configuring GUI: %s" % terminal.label)
                terminal.setup(layouts)  # type: ignore[call-arg]
            else:
                terminal.setup()


    def _clear_events(self) -> None:
        """ Clear the event queue after all events have been delivered. """
        #if(self._event_queue):
        #    print("Clearing event queue: ", self._event_queue)
        self._event_queue.clear()

    def _debug_display_events(self) -> None:
        """ Display all events to console. """
        if not self.debug_show_events:
            return
        for event in self._event_queue:
            print("*********", event)

    def activate_controller(self,
                            label: Optional[str] = None,
                            controller: Optional[_ControllerBase] = None) -> None:
        """ Set a specified controller as the active one.
        Args:
            label: If set, the active controller will be the one matching "label"
                   parameter.
            controller: If set, the active controller will be the one matching
                   this instance. If no matching instance is found, it will be
                   added as a candidate and activated.
        """
        def _activate(candidate: _ControllerBase) -> None:
            """ Set specified controller as the active one. """
            if self.active_controller:
                self.active_controller.active = False
            self.active_controller = candidate

        def _only_one_active() -> None:
            """ Set "active" flag on the active_controller. """
            assert self.active_controller, "No active controller set."
            for candidate_controller in self.controllers.values():
                if candidate_controller is self.active_controller:
                    candidate_controller.active = True
                else:
                    candidate_controller.active = False

        for candidate_controller in self.controllers.values():
            if candidate_controller.label == "debug":
                _activate(candidate_controller)
                candidate_controller.active = False
        for candidate_controller in self.controllers.values():
            if candidate_controller.active:
                _activate(candidate_controller)
                break
        for candidate_controller in self.controllers.values():
            if candidate_controller.label == label:
                _activate(candidate_controller)
                break
        for candidate_controller in self.controllers.values():
            if candidate_controller is controller:
                _activate(candidate_controller)
                break
        if not self.active_controller and not controller:
            # Don't have an self.active_controller yet.
            # Let's just take the first.
            self.active_controller = list(self.controllers.values())[0]

        if self.active_controller and not controller:
            _only_one_active()
            return
        if (self.active_controller and controller and
                self.active_controller.label == controller.label):
            _only_one_active()
            return
        if self.active_controller and self.active_controller is controller:
            _only_one_active()
            return

        # Label was not specified as one of the input arguments.
        assert label is None, "Could not find controller matching '%s'" % label
        assert controller, "Controller not passed in as an argument."

        # This is a new controller.
        self.controllers[controller.label] = controller
        self.all_components.append(controller)
        self.active_controller = controller
        _only_one_active()

    def _active_controller_on_event(self, event_name: str, event_value: bool) -> None:
        """ Make whichever controller has it's "active" property set the active
            one. """

        event_controller_name, event_name = event_name.split(":", maxsplit=1)
        assert event_name == "active", "Unexpected event name: %s" % event_name

        if self.controllers[event_controller_name].active == event_value:
            # No change
            return

        print("New active controller: %s is %s" % (event_controller_name, event_value))

        assert event_controller_name in self.controllers, \
                "Event received from invalid controller."
        if event_value:
            for controller in self.controllers.values():
                controller.active = False
        self.controllers[event_controller_name].active = event_value

        # This will check only one controller has the active flag set
        # or assign the "debug" controller active if none are set.
        self.activate_controller()

        for controller_name, controller in self.controllers.items():
            self.publish_one_by_value("%s:active" % controller_name, controller.active)

    def _copy_active_controller_events(self) -> None:
        """ All controllers publish events under their own name. Subscribers
        are usually only interested in the active controller.
        Here we make copies of the active controller's events under the name
        "active_controller:xxxx" to save working this out on every consumer."""
        assert self.active_controller, "No active controller."

        active = self.active_controller.label
        tmp_event_queue: Deque[Tuple[str, Any]] = deque()
        for event_name, event_value in self._event_queue:
            if not isinstance(event_name, str):
                continue
            if event_name.find(":") < 0:
                continue
            component, event = event_name.split(":", maxsplit=1)
            if component != active:
                continue
            tmp_event_queue.append(("active_controller:%s" % event, event_value))

        self._event_queue.extend(tmp_event_queue)

    def update_components(self) -> bool:
        """ Iterate through all components, delivering and acting upon events. """
        for terminal in self.terminals.values():
            self.running = self.running and terminal.early_update()

        for interface in self.interfaces.values():
            interface.early_update()

        for controller in self.controllers.values():
            controller.early_update()

        # Publish all events.
        self.publish()
        for component in self.all_components:
            component.publish()

        self._copy_active_controller_events()

        # Deliver all events to consumers.
        self.receive()
        for component in self.all_components:
            component.receive()

        self._debug_display_events()
        self._clear_events()

        self._update()
        self._delivered.clear()
        for component in self.all_components:
            #if component._delivered:
            #    print(component.label, component._delivered)
            #else:
            #    print(component.label)

            component._update()
            component.update()
            component._delivered.clear()

        return self.running

    def close(self) -> None:
        """ Cleanup components on shutdown. """
        for controller in self.controllers.values():
            controller.disconnect()
        for terminal in self.terminals.values():
            terminal.close()
