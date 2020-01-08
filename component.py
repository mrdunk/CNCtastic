from typing import List, Dict, Any, Tuple, Deque
from collections import deque

from pygcode import block, Machine

from definitions import FlagState, State, Command, ConnectionState

class _ComponentBase:
    """ General methods required by all components. """

    # Mapping of event names to callback methods or property names.
    eventActions: Dict = {
            # "$COMPONENTNAME:$DESCRIPTION": ("$METHODNAME", None),
            # "$COMPONENTNAME:$DESCRIPTION": ("$METHODNAME", $DEFAULTVALUE),
            # "$COMPONENTNAME:$DESCRIPTION": ("$PROPERTYNAME", $DEFAULTVALUE)
            }

    Event = Tuple[str, Any]
    # Single instance for all instances.
    _eventQueue: Deque[Event] = deque()
    # Unique copy per instance.
    exported: Dict[str, str] = {
            # EVENT_NAME : CLASS_PROPERTY_TO_EXPORT
            }
    _subscriptions: Dict[str, Any]
    _delivered: Deque[Any]
   
    def __init__(self, label: str):
        self.label: str = label
        #self.exported = {}
        self._subscriptions = {}
        self._delivered = deque()

        # Make sure we are subscribed to all the events we have handlers for.
        for event in self.eventActions:
            if event not in self._subscriptions:
                self._subscriptions[event] = None

    def keyGen(self, tag):
        return "%s:%s" % (self.label, tag)

    def service(self):
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        pass

    def publish(self, eventName: str = "", prop=None):
        """ Publish all events listed in the self.exported collection. """
        if not hasattr(self, "exported"):
            return

        if not eventName:
            # Use self.exported and publish all events listed.
            self._publishAllRegistered()
            return

        if eventName and prop is None:
            if eventName not in self.exported:
                raise AttributeError("Property for event \"%s\" not listed in %s"
                        (eventName, self.exported))
            prop = self.exported[eventName]

        self.publishOneByValue(eventName, prop)

    def _publishAllRegistered(self):
        """ Publish events for all listed in self.exported. """
        for eventName, prop in self.exported.items():
            self._publishOneByKey(eventName, prop)

    def _publishOneByKey(self, eventName: str, prop: str):

        # Convert a string reperesentation of an object property into that property.
        totalProperty = self
        for p in prop.split("."):  # TODO: Don't split every time?
            if isinstance(totalProperty, dict) and p in totalProperty:
                totalProperty = totalProperty[p]
            elif (isinstance(totalProperty, List) and
                    p.isnumeric() and int(p) < len(totalProperty)):
                totalProperty = totalProperty[int(p)]
            elif hasattr(totalProperty, p):
                totalProperty = getattr(totalProperty, p)
            else:
                raise AttributeError("Invalid property \"%s\" in %s." %
                        (prop, self.exported))
        self.publishOneByValue(eventName, totalProperty)
        

    def publishOneByValue(self, eventName: str, eventValue):
        """ Distribute an event to all subscribed components. """
        self._eventQueue.append((eventName, eventValue))

    def receive(self):
        """ Deliver events this object is subscribed to. """
        #print(self.label, "receive", self._eventQueue)
        if not hasattr(self, "_subscriptions"):
            return

        for event, value in self._eventQueue:
            if event in self._subscriptions:
                self._delivered.append((event, value))

    def processDeliveredEvents(self):
        """ Do something useful with the received events. """
        # for event in self._delivered:
        #     print(self.label, event)
        pass


    def _processDeliveredEvents(self):
        """ Populate class variables and callbacks in response to configured events. """

        # This will be done after /all/ events have been delivered for all
        # components and the existing event queue cleared.
        # Some of the actions performed by this method will cause new events to be
        # scheduled, mixing events from this round with the next.

        for event in self._delivered:
            eventName, eventValue = event
            action, defaultValue = self.eventActions[eventName]

            if eventValue is None:
                # Use the one configured in this class.
                eventValue = defaultValue

            if not isinstance(action, str):
                raise AttributeError("Action (in self.eventActions) should be a "
                                     "string of the property name")
            if not hasattr(self, action):
                raise AttributeError("Property for event \"%s\" does not exist.")
            callback = getattr(self, action)
            if callable(callback):
                # Refers to a class method.
                callback(eventValue)
            else:
                # Refers to a class variable.
                setattr(self, action, eventValue)

