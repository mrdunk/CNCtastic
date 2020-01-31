# Pylint seems to be looking at python2.7's PySimpleGUI libraries so we need the following:
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" A controller for use when testing which mimics an actual hardware controller. """

from typing import List
try:
    from typing import Literal              # type: ignore
except ImportError:
    from typing_extensions import Literal   # type: ignore
import time
from collections import deque

#import PySimpleGUIQt as sg
from terminals.gui import sg

from controllers._controllerBase import _ControllerBase
from definitions import ConnectionState

CONNECT_DELAY = 4   # seconds
PUSH_DELAY = 1      # seconds

class DebugController(_ControllerBase):
    """ A controller for use when testing which mimics an actual hardware controller. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    # Mimic GRBL compatibility in this controller.
    # https://github.com/gnea/grbl/wiki/Grbl-v1.1-Commands
    SUPPORTED_GCODE = set((
        "G00", "G01", "G02", "G03", "G38.2", "G38.3", "G38.4", "G38.5", "G80",
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
        self.gcode: deque = deque()
        self._connect_time: float = 0
        self._last_receive_data_at: float = 0

    def gui_layout(self) -> List:
        """ Layout information for the PySimpleGUI interface. """
        layout = [
            [sg.Text("Title:", size=(20, 1)),
             sg.Text(self.label, key=self.key_gen("label"), size=(20, 1)),
             sg.Checkbox("Active", default=self.active, key=self.key_gen("active"))],
            [sg.Text("Connection state:", size=(20, 1)),
             sg.Text(size=(18, 1), key=self.key_gen("connection_status"))],
            [sg.Text("Desired:", size=(20, 1)),
             sg.Text(size=(18, 1), key=self.key_gen("desired_connection_status"))],
            [sg.Multiline(default_text="gcode", size=(60, 10), key=self.key_gen("gcode"),
                          autoscroll=True, disabled=True)],
            [sg.Button('Connect', key=self.key_gen("connect"), size=(10, 1), pad=(2, 2)),
             sg.Button('Disconnect', key=self.key_gen("disconnect"), size=(10, 1), pad=(2, 2)),
             sg.Exit(size=(10, 1), pad=(2, 2))
             ],
            ]
        return layout

    def connect(self) -> Literal[ConnectionState]:
        if self.connection_status in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connection_status

        self.set_connection_status(ConnectionState.CONNECTING)
        self._connect_time = time.time()
        return self.connection_status

    def disconnect(self) -> Literal[ConnectionState]:
        if self.connection_status in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connection_status

        self.set_connection_status(ConnectionState.DISCONNECTING)
        self._connect_time = time.time()

        self.ready_for_data = False

        return self.connection_status

    def early_update(self) -> None:
        if self.connection_status != self.desired_connection_status:
            if time.time() - self._connect_time >= CONNECT_DELAY:
                if self.connection_status == ConnectionState.CONNECTING:
                    self.set_connection_status(ConnectionState.CONNECTED)
                elif self.connection_status == ConnectionState.DISCONNECTING:
                    self.set_connection_status(ConnectionState.NOT_CONNECTED)

            if self.desired_connection_status == ConnectionState.CONNECTED:
                self.connect()
            elif self.desired_connection_status == ConnectionState.NOT_CONNECTED:
                self.disconnect()

        if self.connection_status == ConnectionState.CONNECTED:
            if time.time() - self._last_receive_data_at >= PUSH_DELAY:
                self.ready_for_data = True
        else:
            self.ready_for_data = False

    def update(self) -> None:
        super().update()

        if self.ready_for_data and self._queued_updates:
            # Process local buffer.
            self._last_receive_data_at = time.time()
            update = self._queued_updates.popleft()
            jog = update.jog.name
            gcode = update.gcode

            self.gcode.append((jog, gcode))
            if self.debug_show_events:
                print("CONTROLLER: %s  RECEIVED: %s  BUFFER: %s" %
                      (self.label, gcode.gcodes, len(self.gcode)))

            gcode_debug_output = ""
            for jog, gcode_ in self.gcode:
                gcode_debug_output += "%s ; jog=%s ; supported=%s\n" % (
                    str(gcode_.gcodes), jog, self.is_gcode_supported(gcode_.gcodes))
            self.publish_one_by_value(self.key_gen("gcode"), gcode_debug_output)
