""" Code required by all components. """

from typing import Dict, Any, Tuple, Deque, Optional
from collections import deque

class _ComponentBase:
    """ General methods required by all components. """

    Event = Tuple[str, Any]
    # Single shared instance for all components.
    _delayed_event_queue: Deque[Event] = deque()
    _event_queue: Deque[Event] = deque()
    _delay_events = [False,]

    # Unique copy per instance.
    event_subscriptions: Dict[str, Any]
    _delivered: Deque[Any]

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = False

    # Overridden in base classes to be one of "controller", "interface" or "terminal".
    plugin_type: Optional[str] = None

    def __init__(self, label: str) -> None:
        self.label: str = label

        # Events to be delivered to this class with callback as value.
        if not hasattr(self, "event_subscriptions"):
            self.event_subscriptions: Dict[str, Any] = {
                # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", None),
                # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", $DEFAULTVALUE),
                # "$COMPONENTNAME:$DESCRIPTION": ("$PROPERTYNAME", $DEFAULTVALUE)
                }

        self._delivered = deque()

        self.debug_show_events = False

    @classmethod
    def get_classname(cls) -> str:
        """ Return class name. """
        return cls.__qualname__

    def key_gen(self, tag: str) -> str:
        """ Return an event name prepended with the component name.
        eg: "componentName:event_name". """
        return "%s:%s" % (self.label, tag)

    # pylint: disable=R0201 # Method could be a function (no-self-use)
    def early_update(self) -> bool:
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        return True

    def publish(self, event_name: str, event_value: Any) -> None:
        """ Distribute an event to all subscribed components. """
        if self._delay_events[0]:
            print("##delayed", (event_name, event_value))
            self._delayed_event_queue.append((event_name, event_value))
        else:
            self._event_queue.append((event_name, event_value))

    def receive(self) -> None:
        """ Receive events this object is subscribed to. """
        #print(self.label, "receive", self._event_queue)
        if not hasattr(self, "event_subscriptions"):
            return

        # Put any events that arrive from now on in the `_delayed_event_queue`
        # instead of the regular `_event_queue`.
        self._delay_events[0] = True

        for event, value in self._event_queue:
            if event in self.event_subscriptions:
                self._delivered.append((event, value))

    def update(self) -> None:
        """ Called after events get delivered. """
        # for event in self._delivered:
        #     print(self.label, event)

    def _update(self) -> None:
        """ Populate class variables and callbacks in response to configured events. """

        # This will be done after /all/ events have been delivered for all
        # components and the existing event queue cleared.
        # Some of the actions performed by this method will cause new events to be
        # scheduled.

        for event_name, event_value in self._delivered:
            action, default_value = self.event_subscriptions[event_name]

            if event_value is None:
                # Use the one configured in this class.
                event_value = default_value

            if not isinstance(action, str):
                raise AttributeError("Action (in self.event_subscriptions) should be a "
                                     "string of the property name")
            if not hasattr(self, action):
                raise AttributeError("Property for event \"%s\" does not exist." % action)

            callback = getattr(self, action)
            if callable(callback):
                # Refers to a class method.
                try:
                    callback(event_value)
                except TypeError:
                    callback(event_name, event_value)
            else:
                # Refers to a class variable.
                setattr(self, action, event_value)
