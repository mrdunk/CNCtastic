from typing import List, Dict, Any, Tuple, Deque, Optional, Union
from collections import deque

from definitions import FlagState, ConnectionState

class _ComponentBase:
    """ General methods required by all components. """

    Event = Tuple[str, Any]
    # Single shared instance for all components.
    _eventQueue: Deque[Event] = deque()
    # Unique copy per instance.
    eventSubscriptions: Dict[str, Any]
    eventsToPublish: Dict[str, str] 
    _delivered: Deque[Any]
   
    def __init__(self, label: str) -> None:
        self.label: str = label

        # Events to be delivered to this class with callback as value.
        if not hasattr(self, "eventSubscriptions"):
            self.eventSubscriptions: Dict[str, Any] = {
                    # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", None),
                    # "$COMPONENTNAME:$DESCRIPTION": ("$CALLBACK", $DEFAULTVALUE),
                    # "$COMPONENTNAME:$DESCRIPTION": ("$PROPERTYNAME", $DEFAULTVALUE)
                    }

        # Variables to automatically export when publish() method is called.
        # TODO: This isn't actually used. Will it be useful in the future?
        #       Should we remove it?
        if not hasattr(self, "eventsToPublish"):
            self.eventsToPublish = {
                # EVENT_NAME : CLASS_PROPERTY_TO_EXPORT
                }

        self._delivered = deque()

        self.debugShowEvents = False

    def keyGen(self, tag: str) -> str:
        return "%s:%s" % (self.label, tag)

    def earlyUpdate(self) -> None:
        """ To be called periodically.
        Any housekeeping tasks should happen here. """
        pass

    def publish(self, eventName: str = "", prop: Optional[str]=None) -> None:
        """ Publish all events listed in the self.eventsToPublish collection. """
        if not hasattr(self, "eventsToPublish"):
            return

        if not eventName:
            # Use self.eventsToPublish and publish all events listed.
            self._publishAllRegistered()
            return

        if eventName and prop is None:
            if eventName not in self.eventsToPublish:
                raise AttributeError("Property for event \"%s\" not listed in %s" %
                        (eventName, self.eventsToPublish))
            prop = self.eventsToPublish[eventName]

        self.publishOneByValue(eventName, prop)

    def _publishAllRegistered(self) -> None:
        """ Publish events for all listed in self.eventsToPublish. """
        for eventName, prop in self.eventsToPublish.items():
            self._publishOneByKey(eventName, prop)

    def _publishOneByKey(self, eventName: str, prop: str) -> None:

        # Convert a string representation of an object property into that property.
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
                        (prop, self.eventsToPublish))
        self.publishOneByValue(eventName, totalProperty)
        

    def publishOneByValue(self,
                          eventName: str,
                          eventValue: Any) -> None:
        """ Distribute an event to all subscribed components. """
        self._eventQueue.append((eventName, eventValue))

    def receive(self) -> None:
        """ Deliver events this object is subscribed to. """
        #print(self.label, "receive", self._eventQueue)
        if not hasattr(self, "eventSubscriptions"):
            return

        for event, value in self._eventQueue:
            if event in self.eventSubscriptions:
                self._delivered.append((event, value))

    def updateEarly(self) -> None:
        """ Called before events get delivered. """
        pass

    def update(self) -> None:
        """ Called after events get delivered. """
        # for event in self._delivered:
        #     print(self.label, event)
        pass


    def _update(self) -> None:
        """ Populate class variables and callbacks in response to configured events. """

        # This will be done after /all/ events have been delivered for all
        # components and the existing event queue cleared.
        # Some of the actions performed by this method will cause new events to be
        # scheduled, mixing events from this round with the next.

        for event in self._delivered:
            eventName, eventValue = event
            action, defaultValue = self.eventSubscriptions[eventName]

            if eventValue is None:
                # Use the one configured in this class.
                eventValue = defaultValue

            if not isinstance(action, str):
                raise AttributeError("Action (in self.eventSubscriptions) should be a "
                                     "string of the property name")
            if not hasattr(self, action):
                raise AttributeError("Property for event \"%s\" does not exist." % action)

            callback = getattr(self, action)
            if callable(callback):
                # Refers to a class method.
                try:
                    callback(eventValue)
                except TypeError:
                    callback(eventName, eventValue)
            else:
                # Refers to a class variable.
                setattr(self, action, eventValue)

