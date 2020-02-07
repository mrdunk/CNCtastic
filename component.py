""" Code required by all components. """

from typing import List, Dict, Any, Tuple, Deque, Optional
from collections import deque

class _ComponentBase:
    """ General methods required by all components. """

    Event = Tuple[str, Any]
    # Single shared instance for all components.
    _event_queue: Deque[Event] = deque()

    # Unique copy per instance.
    event_subscriptions: Dict[str, Any]
    events_to_publish: Dict[str, str]
    _delivered: Deque[Any]

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = False

    def __init__(self, label: str) -> None:
        self.label: str = label

        # Events to be delivered to this class with callback as value.
        if not hasattr(self, "event_subscriptions"):
            self.event_subscriptions: Dict[str, Any] = {
                # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", None),
                # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", $DEFAULTVALUE),
                # "$COMPONENTNAME:$DESCRIPTION": ("$PROPERTYNAME", $DEFAULTVALUE)
                }

        # Variables to automatically export when publish() method is called.
        # TODO: This isn't actually used. Will it be useful in the future?
        #       Should we remove it?
        if not hasattr(self, "events_to_publish"):
            self.events_to_publish = {
                # EVENT_NAME : CLASS_PROPERTY_TO_EXPORT
                }

        self._delivered = deque()

        self.debug_show_events = False

    @classmethod
    def get_classname(cls):
        """ Return class name. """
        return cls.__name__

    def key_gen(self, tag: str) -> str:
        """ Return an event name prepended with the component name.
        eg: "componentName:event_name". """
        return "%s:%s" % (self.label, tag)

    def early_update(self) -> None:
        """ To be called periodically.
        Any housekeeping tasks should happen here. """

    def publish(self, event_name: str = "", property_: Optional[str] = None) -> None:
        """ Publish all events listed in the self.events_to_publish collection. """
        if not hasattr(self, "events_to_publish"):
            return

        if not event_name:
            # Use self.events_to_publish and publish all events listed.
            self._publish_all_registered()
            return

        if event_name and property_ is None:
            if event_name not in self.events_to_publish:
                raise AttributeError("Property for event \"%s\" not listed in %s" %
                                     (event_name, self.events_to_publish))
            property_ = self.events_to_publish[event_name]

        self.publish_one_by_value(event_name, property_)

    def _publish_all_registered(self) -> None:
        """ Publish events for all listed in self.events_to_publish. """
        for event_name, property_ in self.events_to_publish.items():
            self._publish_one_by_key(event_name, property_)

    def _publish_one_by_key(self, event_name: str, property_: str) -> None:

        # Convert a string representation of an object property into that property.
        total_property = self
        for prop in property_.split("."):  # TODO: Don't split every time?
            if isinstance(total_property, dict) and prop in total_property:
                total_property = total_property[prop]
            elif (isinstance(total_property, List) and
                  prop.isnumeric() and int(prop) < len(total_property)):
                total_property = total_property[int(prop)]
            elif hasattr(total_property, prop):
                total_property = getattr(total_property, prop)
            else:
                raise AttributeError("Invalid property \"%s\" in %s." %
                                     (property_, self.events_to_publish))
        self.publish_one_by_value(event_name, total_property)

    def publish_one_by_value(self,
                             event_name: str,
                             event_value: Any) -> None:
        """ Distribute an event to all subscribed components. """
        self._event_queue.append((event_name, event_value))

    def receive(self) -> None:
        """ Receive events this object is subscribed to. """
        #print(self.label, "receive", self._event_queue)
        if not hasattr(self, "event_subscriptions"):
            return

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
        # scheduled, mixing events from this round with the next.

        for event in self._delivered:
            event_name, event_value = event
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
