# pylint: disable=W0223
# Method '_handle_gcode' is abstract in class '_ControllerBase' but is not
# overridden (abstract-method)
""" Base class for hardware controllers that use a serial port to connect. """

from typing import Optional, List, Set
try:
    from typing import Literal              # type: ignore
except ImportError:
    from typing_extensions import Literal   # type: ignore

import os.path
import threading
import serial
import serial.tools.list_ports

from PySimpleGUIQt_loader import sg

from controllers._controller_base import _ControllerBase
from definitions import ConnectionState

SERIAL_INTERVAL = 0.02 # seconds

# Path to grbl-sim instance.
FAKE_SERIAL = "/tmp/ttyFAKE"

class _SerialControllerBase(_ControllerBase):
    """ Base class for hardware controllers that use a serial port to connect. """

    _serial_port_in_use: Set[str] = set()

    def __init__(self, label: str = "serialController") -> None:
        super().__init__(label)
        #self.serial_port = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        self.serial_port: str = ""
        self.serial_baud = 115200
        self._serial = None
        self.testing: bool = False  # Prevent _periodic_io() from blocking during tests.
        self._serial_thread: Optional[threading.Thread] = None
        
        self.event_subscriptions[self.key_gen("device_picker")] = ("set_device", None)
        self.event_subscriptions[self.key_gen("serial_port_edit")] = ("set_device", None)
        self.event_subscriptions[self.key_gen("device_scan")] = ("search_device", None)
        
        self.ports: List[str] = []
        self.device_picker: sg.Combo = None

    def gui_layout_components(self) -> List[List[sg.Element]]:
        """ GUI layout common to all derived classes. """
        components = super().gui_layout_components()

        self.device_picker = sg.Combo(values=["to_populate"],
                                      size=(25, 1),
                                      key=self.key_gen("device_picker"),
                                      default_value=self.serial_port,
                                      enable_events=True,
                                      )
        device_scan = sg.Button("Scan",
                                size=(5, 1),
                                key=self.key_gen("device_scan"),
                                tooltip="Scan for serial ports.",
                                )

        self.search_device()

        components["view_serial_port"] = [sg.Text("Serial port:"),
                                          sg.Text(self.serial_port,
                                                  key=self.key_gen("serial_port"))]
        components["edit_serial_port"] = [sg.Text("Serial port:"),
                                          self.device_picker, device_scan]
        
        return components

    def set_device(self, device: str) -> None:
        """ Set serial port when selected by menu. """
        print("set_device", device)
        if not device:
            return

        # Disconnect from any other serial port.
        # TODO: Move this to the Save method?
        self.disconnect()

        self.device_picker.Update(value = device)
        self._modify_controller(self.key_gen("serial_port_edit"), device)

    def search_device(self, _: str = "", __: None = None) -> None:
        """ Search system for serial ports. """
        self.ports = [x.device for x in serial.tools.list_ports.comports() \
                  if x.vid is not None \
                  and  x.pid is not None \
                  and x.device is not None]

        if os.path.exists(FAKE_SERIAL):
            self.ports.append(FAKE_SERIAL)

        if not self.ports:
            self.ports.append("No serial ports autodetected")

        # print("Found ports {}".format(self.ports))
        
        if self.serial_port not in self.ports:
            self.ports.append(self.serial_port)

        if not self.serial_port:
            self.serial_port = self.ports[0]

        try:
            self.device_picker.Update(values=self.ports,
                                      value=self.serial_port
                                      )
            print("search_device", self.serial_port)
        except AttributeError:
            # self.device_picker not configured.
            pass

    def connect(self) -> Literal[ConnectionState]:
        """ Try to open serial port. Set connection_status to CONNECTING. """
        # print("connect")
        if self.connection_status in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connection_status

        if self.serial_port in self._serial_port_in_use:
            self.connection_status = ConnectionState.BLOCKED
            return self.connection_status

        self.set_connection_status(ConnectionState.CONNECTING)

        try:
            self._serial = serial.serial_for_url(
                self.serial_port, self.serial_baud, timeout=0)
        except AttributeError:
            try:
                self._serial = serial.Serial(
                    self.serial_port, self.serial_baud, timeout=0)
            except serial.serialutil.SerialException:
                self.set_connection_status(ConnectionState.MISSING_RESOURCE)
        except serial.serialutil.SerialException:
            self.set_connection_status(ConnectionState.MISSING_RESOURCE)

        self._serial_port_in_use.add(self.serial_port)
        return self.connection_status

    def disconnect(self) -> Literal[ConnectionState]:
        """ Close serial port, shut down serial port thread, etc.
        Set connection_status to DISCONNECTING. """
        if self.connection_status in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connection_status
        if self.connection_status in [
                ConnectionState.CONNECTED,
                ConnectionState.CONNECTING]:
            print("Disconnecting %s %s" % (self.label, self.serial_port))

        self.set_desired_connection_status(ConnectionState.NOT_CONNECTED)
        self.ready_for_data = False

        if self._serial is None:
            self.set_connection_status(ConnectionState.NOT_CONNECTED)
        else:
            self.set_connection_status(ConnectionState.DISCONNECTING)

            self._serial_thread.join()
            self._serial.close()

        self.ready_for_data = False

        return self.connection_status

    def on_connected(self) -> None:
        """ Executed when serial port first comes up.
        Check serial port is open then start serial port thread.
        Set connection_status to CONNECTED. """
        if self._serial is None:
            self.set_connection_status(ConnectionState.FAIL)
            return

        if not self._serial.is_open:
            return

        print("Connected %s %s" % (self.label, self.serial_port))
        self.set_connection_status(ConnectionState.CONNECTED)

        # Drain the buffer of any noise.
        self._serial.flush()
        while self._serial.readline():
            pass

        self._serial_thread = threading.Thread(target=self._periodic_io)
        self._serial_thread.daemon = True
        self._serial_thread.start()

    def on_disconnected(self) -> None:
        """ Executed when serial port is confirmed closed.
        Check serial port was closed then set connection_status to NOT_CONNECTED. """
        if self._serial is None:
            self.set_connection_status(ConnectionState.FAIL)
            return

        if self._serial.is_open:
            return

        print("Serial disconnected.")
        self.set_connection_status(ConnectionState.NOT_CONNECTED)
        self._serial_port_in_use.discard(self.serial_port)
        self._serial = None

        self.publish(self.key_gen("state"),
                                  "Connection state: %s" %
                                  self.connection_status.name)
        #self.search_device()

    def _serial_write(self, data: bytes) -> bool:
        """ Send data to serial port. """
        if self._serial is None:
            self.set_connection_status(ConnectionState.FAIL)
            return False

        try:
            self._serial.write(data)
        except serial.serialutil.SerialException:
            self.set_connection_status(ConnectionState.FAIL)
            return False
        return True

    def _serial_read(self) -> bytes:
        """ Read data from serial port. """
        if self._serial is None:
            self.set_connection_status(ConnectionState.FAIL)
            return b""

        try:
            if not self._serial.inWaiting():
                return b""
        except OSError:
            self.set_connection_status(ConnectionState.FAIL)

        line = None
        try:
            line = self._serial.readline()
        except serial.serialutil.SerialException:
            self.set_connection_status(ConnectionState.FAIL)
        return line

    def early_update(self) -> None:
        """ Called early in the event loop, before events have been received. """
        if self.connection_status != self.desired_connection_status:
            # Transition between connection states.
            if self.connection_status is ConnectionState.CONNECTING:
                # Connection process already started.
                self.on_connected()

            elif self.connection_status is ConnectionState.DISCONNECTING:
                # Trying to disconnect.
                self.on_disconnected()

            elif self.connection_status in [ConnectionState.FAIL,
                                            ConnectionState.MISSING_RESOURCE,
                                            ConnectionState.BLOCKED]:
                # A serial port error occurred either # while opening a serial port or
                # on an already open port.
                self.publish(self.key_gen("state"),
                                          "Connection state: %s" %
                                          self.connection_status.name)
                self.set_desired_connection_status(ConnectionState.NOT_CONNECTED)
                self.set_connection_status(ConnectionState.CLEANUP)

            elif self.desired_connection_status is ConnectionState.CONNECTED:
                # Start connection process.
                self.connect()

            elif self.desired_connection_status is ConnectionState.NOT_CONNECTED:
                # Start disconnection.
                self.disconnect()

    def _periodic_io(self) -> None:
        """ Read from and write to serial port.
            Called from a separate thread.
            Blocks while serial port remains connected. """
        # while self.connection_status is ConnectionState.CONNECTED:
        #     print("do read and write here.")
        #     self._time.sleep(SERIAL_INTERVAL)
        #     if self.testing:
        #         break

    def update(self) -> None:
        super().update()

        if not self.ports:
            self.search_device()
