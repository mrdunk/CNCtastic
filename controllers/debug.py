# Pylint seems to be looking at python2.7's PySimpleGUI libraries so we need the following:
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" A controller for use when testing which mimics an actual hardware controller. """

from typing import List, Callable, Any, Deque, Tuple
try:
    from typing import Literal              # type: ignore
except ImportError:
    from typing_extensions import Literal   # type: ignore
import time
from collections import deque

from pygcode import Machine, GCodeCoordSystemOffset, \
                    GCodeResetCoordSystemOffset, Block

from PySimpleGUIQt_loader import sg

from definitions import ConnectionState
from controllers._controller_base import _ControllerBase
from controllers.state_machine import StateMachineBase

CONNECT_DELAY = 4   # seconds
PUSH_DELAY = 1      # seconds

class DebugController(_ControllerBase):
    """ A controller for use when testing which mimics an actual hardware controller. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    # Limited by pygcode's virtual machine:
    # https://github.com/fragmuffin/pygcode/wiki/Supported-gcodes
    # TODO: Prune this list back to only those supported.
    SUPPORTED_GCODE = set((
        "G00", "G01", "G02", "G03",
        "G54", "G55", "G56", "G57", "G58", "G59",
        "G17", "G18", "G19",
        "G90", "G91",
        "G91.1",
        "G93", "G94",
        "G20", "G21",
        "G40",
        "G43.1", "G49",
        "M00", "M01", "M02", "M30",
        "M03", "M04", "M05",
        "M07", "M08", "M09",
        "G04", "G10 L2", "G10 L20", "G28", "G30", "G28.1", "G30.1", "G53", "G92", "G92.1",
        ))

    def __init__(self, label: str = "debug") -> None:
        super().__init__(label)

        # A record of all gcode ever sent to this controller.
        self.log: Deque[Tuple[str, str, Any]] = deque()

        self._connect_time: float = 0
        self._last_receive_data_at: float = 0

        # State machine reflecting _virtual_cnc state.
        self.state: StateMachinePygcode = StateMachinePygcode(self.publish_from_here)

        # Allow replacing with a mock version when testing.
        self._time: Any = time

    def gui_layout_view(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        
        components = self.gui_layout_components()
        layout = [
                    components["view_label"],
                    [sg.Multiline(default_text="gcode",
                                  size=(60, 10),
                                  key=self.key_gen("gcode"),
                                  autoscroll=True,
                                  disabled=True)],
                    components["view_connection"],
                    components["view_buttons"],
                ]
        return layout

    def gui_layout_edit(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        
        components = self.gui_layout_components()
        layout = [
                    components["edit_label"],
                    components["edit_buttons"],
                ]
        return layout

    def connect(self) -> Literal[ConnectionState]:
        if self.connection_status in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connection_status

        self.set_connection_status(ConnectionState.CONNECTING)
        self._connect_time = self._time.time()
        return self.connection_status

    def disconnect(self) -> Literal[ConnectionState]:
        if self.connection_status in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connection_status

        self.set_connection_status(ConnectionState.DISCONNECTING)
        self._connect_time = self._time.time()

        self.ready_for_data = False

        return self.connection_status

    def early_update(self) -> None:
        if self.connection_status != self.desired_connection_status:
            if self._time.time() - self._connect_time >= CONNECT_DELAY:
                if self.connection_status == ConnectionState.CONNECTING:
                    self.set_connection_status(ConnectionState.CONNECTED)
                elif self.connection_status == ConnectionState.DISCONNECTING:
                    self.set_connection_status(ConnectionState.NOT_CONNECTED)

            if self.desired_connection_status == ConnectionState.CONNECTED:
                self.connect()
            elif self.desired_connection_status == ConnectionState.NOT_CONNECTED:
                self.disconnect()

        if self.connection_status == ConnectionState.CONNECTED:
            if self._time.time() - self._last_receive_data_at >= PUSH_DELAY:
                self.ready_for_data = True
        else:
            self.ready_for_data = False

    def update(self) -> None:
        super().update()
        if self._queued_updates:
            self._last_receive_data_at = self._time.time()

            # Process local event buffer.
            for event, data in self._queued_updates:
                # Generate output for debug log.
                component_name, action = event.split(":", 1)
                self.log.append((component_name, action, data))

                debug_output = ""
                for log_line in self.log:
                    debug_output += "%s\t%s\t%s\n" % log_line
                self.publish(self.key_gen("gcode"), debug_output)

            # Update the state machine to reflect the pygcode virtual machine.
            self.state.update()

    def _handle_gcode(self, gcode_block: Block) -> None:
        """ Update the virtual machine with incoming gcode. """

        # Gcode which deals with work offsets is not handled correctly by _virtual_cnc.
        # Track and update self.state offsets here instead.
        for gcode in gcode_block.gcodes:
            if isinstance(gcode, GCodeCoordSystemOffset):
                work_offset = {}
                for key, value in gcode.get_param_dict().items():
                    work_offset[key.lower()] = self.state.machine_pos[key.lower()] - value
                self.state.work_offset = work_offset
                return
            if isinstance(gcode, GCodeResetCoordSystemOffset):
                self.state.work_offset = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
                return
            # TODO Check for more gcode in same block.

        # _virtual_cnc can handle all other gcode.
        self.state.proces_gcode(gcode_block)


class StateMachinePygcode(StateMachineBase):
    """ State Machine reflecting the state of a pygcode virtual machine.
        https://github.com/fragmuffin/pygcode/wiki/Interpreting-gcode """

    def __init__(self, on_update_callback: Callable[[str, Any], None]) -> None:
        super().__init__(on_update_callback)
        self._virtual_cnc = Machine()

    def update(self) -> None:
        """ Populate this state machine values from self._virtual_cnc. """
        self._parse_modal()
        self.machine_pos = self._virtual_cnc.pos.values
        self.feed_rate = self._virtual_cnc.mode.feed_rate.word.value

    def _parse_modal(self) -> None:
        """ Update current modal group values. """
        for modal in self._virtual_cnc.mode.gcodes:
            modal_bytes = str(modal).encode('utf-8')
            if modal_bytes in self.MODAL_COMMANDS:
                modal_group = self.MODAL_COMMANDS[modal_bytes]
                self.gcode_modal[modal_group] = modal_bytes
            elif chr(modal_bytes[0]).encode('utf-8') in self.MODAL_COMMANDS:
                modal_group = self.MODAL_COMMANDS[chr(modal_bytes[0]).encode('utf-8')]
                self.gcode_modal[modal_group] = modal_bytes
            else:
                print("TODO: ", modal)
        # print(self.gcode_modal)

    def proces_gcode(self, gcode_block: Block) -> None:
        """ Have the pygcode VM parse incoming gcode. """
        self._virtual_cnc.process_block(gcode_block)
