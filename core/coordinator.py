""" Coordinator handles interactions between components.
Coordinator polls all components for published events and delivers them to
subscribers. """


from typing import List, Dict, Optional, Deque, Tuple, Any, Type
from collections import deque
import sys
from pathlib import Path
import pprint
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
from ruamel.yaml import YAML, YAMLError  # type: ignore

from core.component import _ComponentBase
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
                 controller_classes: List[Type[_ControllerBase]],
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
        self.controller_classes: Dict[str, Type[_ControllerBase]] = \
                {controller.get_classname(): controller for controller in controller_classes}
        self.controllers: Dict[str, _ControllerBase] = {}
        self.terminal_sub_components: Dict[str, Any] = {}

        self.debug_show_events = debug_show_events

        self.active_controller: Optional[_ControllerBase] = None
        self.config: Dict[str, Any] = {}

        self.all_components: List[_ComponentBase] = []
        self.all_components += list(terminals)
        self.all_components += list(interfaces)

        self.event_subscriptions = {}

        self._load_config("config.yaml")
        self._setup_controllers()

        self._setup_terminals()

        self.running = True

    def _setup_controllers(self) -> None:
        self.controllers = {}
        self.all_components = list(
            filter(lambda i: isinstance(i, _ControllerBase) is False,
                   self.all_components))

        if "DebugController" in self.controller_classes:
            instance = self.controller_classes["DebugController"]("debug")
            self.controllers[instance.label] = instance
            self.all_components.append(instance)

        if "controllers" in self.config:
            for label, controller in self.config["controllers"].items():
                assert controller["type"] in self.controller_classes, \
                    "Controller type '%s' specified in config file does not exist." \
                    % controller["type"]
                class_ = self.controller_classes[controller["type"]]
                instance = class_(label)

                for property_, value in controller.items():
                    if hasattr(instance, property_):
                        setattr(instance, property_, value)
                    elif property_ not in ["type"]:  # Ignore any in the list.
                        print("Unrecognised config parameter "
                              "[controller, property, value]: %s, %s, %s" %
                              (label, property_, value))

                self.controllers[label] = instance
                self.all_components.append(instance)

        self.activate_controller()

        # Change which controller is active in response to event.
        for controller in self.controllers:
            self.event_subscriptions["%s:set_active" % controller] = \
                ("_on_activate_controller", None)

        self.event_subscriptions["request_new_controller"] = \
            ("_new_controller", None)

    def _load_config(self, filename: str) -> None:
        path = Path(filename)
        yaml = YAML(typ='safe')
        try:
            self.config = yaml.load(path)
        except YAMLError as error:
            print("--------")
            print("Problem in configuration file: %s" % error.problem_mark.name)
            print("  line: %s  column: %s" %
                  (error.problem_mark.line, error.problem_mark.column))
            print("--------")
            sys.exit(0)

        print("Config:")
        pprint.pprint(self.config)

    def _setup_terminals(self) -> None:
        """ Do configuration that was not possible before all other components
        were instantiated. """
        for terminal in self.terminals.values():
            print("Terminal %s of type %s is being activated." %
                  (terminal.label, terminal.get_classname()))

            terminal.setup(self.interfaces, self.controllers, self.controller_classes)

            # Add sub_components to the list of things to be updated by this
            # controller.
            for label, sub_component in terminal.sub_components.items():
                assert label not in self.terminal_sub_components, \
                       "Duplicate sub component name: %s" % label
                self.terminal_sub_components[label] = sub_component

        self.all_components += list(self.terminal_sub_components.values())

    def _clear_events(self) -> None:
        """ Clear the event queue after all events have been delivered. """
        #if(self._event_queue):
        #    print("Clearing event queue: ", self._event_queue)

        self._delay_events[0] = False
        self._event_queue.clear()

        # Move any events that arrived during `self.receive()` to the main queue.
        while True:
            try:
                event = self._delayed_event_queue.pop()
            except IndexError:
                break
            print("#####copying delayed event.", event)
            self._event_queue.append(event)

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

    def _on_activate_controller(self, event: str, event_value: bool) -> None:
        """ Make whichever controller has it's "active" property set the active
            one. """
        #print("coordinator._on_activate_controller", event, event_value)

        event_controller_name, event_name = event.split(":", maxsplit=1)
        assert event_name == "set_active", "Unexpected event name: %s" % event_name
        assert isinstance(event_value, bool), "Expected value should be boolean."

        if self.controllers[event_controller_name].active == event_value:
            # No change
            self.publish("%s:active" % event_controller_name, event_value)
            return

        print("Controller: %s is %s" %
              (event_controller_name, "active" if event_value else "inactive"))

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
            self.publish("%s:active" % controller_name, controller.active)

    def _copy_active_controller_events(self) -> None:
        """ Copy the active controller's events into the "active_controller:xxxx"
        namespace.
        All controllers publish events under their own name. Subscribers
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

        self._copy_active_controller_events()

        # Deliver all events to consumers.
        self.receive()
        for component in self.all_components:
            component.receive()

        self._debug_display_events()
        self._clear_events()

        self._update()
        #if self._delivered:
        #    print(self.label, self._delivered)
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

    def _new_controller(self, event: str, controller_class: str) -> None:
        print("_new_controller", event, controller_class)
        instance = self.controller_classes[controller_class]("new")
        self.controllers[instance.label] = instance
        self.all_components.append(instance)
        self.activate_controller(controller=instance)
        self.publish(self.key_gen("new_controller"), instance.label)
        self.event_subscriptions["new:set_active"] = \
            ("_on_activate_controller", None)
