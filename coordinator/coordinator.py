from typing import List, Dict, Any, Tuple, Deque
from collections import deque

from pygcode import block, Machine

from definitions import FlagState, State, Command, ConnectionState, InterfaceState

class _CoreComponent:
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
        """ This should be done after /all/ events have been delivered for all
        components and the existing event queue cleared.
        Some of the actions performed by this method will cause new events to be
        scheduled, mixing events from this round with the next.
        """
        #while self._delivered:
        #    event = self._delivered.popleft()
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

class Coordinator(_CoreComponent):
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
        self.state: State
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
            self.state = candidate.state

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
        self.state = self.activeController.state

    def update(self) -> bool:
        """ Iterate through all other components and service all data transfer
        requests. """
        self._updateTerminal()
        self._updateInterface()
        self._updateControler()


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

    def _updateTerminal(self):
        for terminalName, terminal in self.terminals.items():
            self.running = self.running and terminal.service()

    def _updateInterface(self):
        for interfaceName, inpt in self.interfaces.items():
            inpt.service()

            if inpt.status is not InterfaceState.UP_TO_DATE:
                next

            if inpt.readyForPush:
                # TODO: This will make state mutable from the interface object.
                # Do we want this? Should we send a copy instead?
                inpt.push(self.state)
            if inpt.readyForPull:
                freshData: UpdateState = inpt.pull()

                self._parseGcode(freshData.gcode, freshData.jog == FlagState.TRUE)        
                if not freshData.halt == FlagState.UNSET:
                    self.state.halt = freshData.halt == FlagState.TRUE
                if not freshData.pause == FlagState.UNSET:
                    self.state.pause = freshData.pause == FlagState.TRUE

    def _updateControler(self):
        assert self.activeController, "No active controller."

        self.activeController.service()

        if not self.activeController.connectionStatus == ConnectionState.CONNECTED:
            return
        
        if self.activeController.readyForPush:
            command = Command()
            command.halt = self.state.halt
            command.pause = self.state.pause
            if self.gcode:
                command.gcode = self.gcode.popleft()
            self.activeController.push(command)

        if self.activeController.readyForPull:
            freshData = self.activeController.pull()
        
    def _parseGcode(self, gcodes: block.Block, jog: bool = False):
        if gcodes is None:
            return

        command = None
        for gcode in gcodes.gcodes:
            if gcode.word_key:
                command = gcode.word_key
                break
        if not self.activeController.isGcodeSupported(command):
            print("Gcode: %s not supported." % command)
            return

        self.state.vm.process_block(gcodes)
        if jog:
            self.gcode.append({"gcode": gcodes, "jog": True})
        else:
            self.gcode.append({"gcode": gcodes})

    def close(self):
        for controller in self.controllers.values():
            controller.disconnect()
        for interface in self.interfaces.values():
            interface.disconnect()
        for terminal in self.terminals.values():
            terminal.close()

