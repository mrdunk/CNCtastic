""" Base class for all CNC machine control hardware. """

from typing import Any, Deque, Set
try:
    from typing import Literal              # type: ignore
except ImportError:
    from typing_extensions import Literal
from collections import deque

from pygcode import Machine, GCodeCoordSystemOffset, \
                    GCodeResetCoordSystemOffset, Block, GCode, Line

from component import _ComponentBase
from definitions import ConnectionState
from controllers.state_machine import StateMachineBase

class _ControllerBase(_ComponentBase):
    """ Base class for all CNC machine control hardware. """

    # Strings of the gcode commands this controller supports.
    SUPPORTED_GCODE: Set[GCode] = set()

    # Type of component. Used by the plugin loader.
    plugin_type = "controller"

    def __init__(self, label: str) -> None:
        super().__init__(label)

        self.__active: bool = False
        self.ready_for_data: bool = False
        self.connection_status: ConnectionState = ConnectionState.UNKNOWN
        self.desired_connection_status: ConnectionState = ConnectionState.NOT_CONNECTED
        self._new_gcode = None
        self._new_move_absolute = None
        self._new_move_relative = None
        self._queued_updates: Deque[Any] = deque()
        self.state = StateMachineBase(self.publish_from_here)

        # Map incoming events to local member variables and callback methods.
        self.label = label
        self.event_subscriptions = {
            self.key_gen("connect"):
                ("set_desired_connection_status", ConnectionState.CONNECTED),
            self.key_gen("disconnect"):
                ("set_desired_connection_status", ConnectionState.NOT_CONNECTED),
            #"desiredState:newGcode": ("_new_gcode_line", None),
            "command:gcode": ("_new_gcode", None),
            "command:move_absolute": ("_new_move_absolute", None),
            "command:move_relative": ("_new_move_relative", None),
            }

        self.set_connection_status(ConnectionState.UNKNOWN)
        self.set_desired_connection_status(ConnectionState.NOT_CONNECTED)

    def publish_from_here(self, variable_name: str, variable_value: Any) -> None:
        """ A method wrapper to pass on to the StateMachineBase so it can
        publish events. """
        self.publish_one_by_value(self.key_gen(variable_name), variable_value)

    @property
    def active(self) -> bool:
        """ Getter. """
        return self.__active

    @active.setter
    def active(self, value: bool) -> None:
        """ Setter. """
        self.__active = value
        if value:
            self.on_activate()
        else:
            self.on_deactivate()

    def on_activate(self) -> None:
        """ Called whenever self.active is set True. """

    def on_deactivate(self) -> None:
        """ Called whenever self.active is set False. """

    def set_desired_connection_status(self, connection_status: Literal[ConnectionState]) -> None:
        """ Set connection status we would like controller to be in.
        The controller should then attemt to transition to this state. """
        self.desired_connection_status = connection_status
        self.publish_one_by_value(self.key_gen("desired_connection_status"), connection_status)

    def set_connection_status(self, connection_status: Literal[ConnectionState]) -> None:
        """ Set connection status of controller. """
        self.connection_status = connection_status
        self.publish_one_by_value(self.key_gen("connection_status"), connection_status)

    def connect(self) -> Literal[ConnectionState]:
        """ Make connection to controller. """
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def disconnect(self) -> Literal[ConnectionState]:
        """ Disconnect from controller. """
        raise NotImplementedError
        return ConnectionState.UNKNOWN

    def is_gcode_supported(self, command: Any) -> bool:
        """ Check a gcode command line contains only supported gcode statements. """
        if isinstance(command, list):
            return_val = True
            for gcode in command:
                return_val = return_val and str(gcode.word_key) in self.SUPPORTED_GCODE
            return return_val
        if isinstance(command, GCode):
            return str(command.word_key) in self.SUPPORTED_GCODE
        if isinstance(command, str):
            return str(command) in self.SUPPORTED_GCODE

        raise AttributeError("Cannot tell if %s is valid gcode." % command)

    def update(self) -> None:
        if(self._delivered and
           self.connection_status is ConnectionState.CONNECTED and
           self.active):
            # Save incoming data to local buffer until it can be processed.
            # (self._delivered will be cleared later this iteration.)
            for event, value in self._delivered:
                ## TODO: Flags.
                if event in ("command:gcode",
                             "command:move_absolute",
                             "command:move_relative"):
                    self._queued_updates.append((event, value))

    def _handle_gcode(self, gcode_block: Block) -> None:
        raise NotImplementedError

    def _handle_move_absolute(self,
                              x: float = 0,
                              y: float = 0,
                              z: float = 0,
                              f: float = 0,
                              feed: float = 0) -> None:
        """ Move machine head to specified coordinates. """
        distance_mode_save = self.state.gcode_modal.get("distance", "G90")

        gcode = "G90 G00 "
        if x is not None:
            gcode += "X%s " % x
        if y is not None:
            gcode += "Y%s " % y
        if z is not None:
            gcode += "Z%s " % z
        if f is not None:
            gcode += "F%s " % f

        self._handle_gcode(Line(gcode).block)

        if distance_mode_save != "G90":
            # Restore modal distance_mode.
            self._handle_gcode(Line(distance_mode_save).block)
    
    def _handle_move_relative(self,
                              x: float = 0,
                              y: float = 0,
                              z: float = 0,
                              f: float = 0,
                              feed: float = 0) -> None:
        """ Move machine head to specified coordinates. """
        distance_mode_save = self.state.gcode_modal.get("distance", "G91")

        gcode = "G91 G00 "
        if x is not None:
            gcode += "X%s " % x
        if y is not None:
            gcode += "Y%s " % y
        if z is not None:
            gcode += "Z%s " % z
        if f is not None:
            gcode += "F%s " % f

        self._handle_gcode(Line(gcode).block)
        
        if distance_mode_save != "G91":
            # Restore modal distance_mode.
            self._handle_gcode(Line(distance_mode_save).block)
