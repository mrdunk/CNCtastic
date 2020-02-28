# pylint: disable=W0223
# Method '_handle_gcode' is abstract in class '_ControllerBase' but is not
# overridden (abstract-method)
""" Base class for hardware controllers that use a serial port to connect. """

from typing import Optional
try:
    from typing import Literal              # type: ignore
except ImportError:
    from typing_extensions import Literal   # type: ignore

import threading
import serial


from controllers._controller_base import _ControllerBase
from definitions import ConnectionState

SERIAL_INTERVAL = 0.02 # seconds


class _SerialControllerBase(_ControllerBase):
    """ Base class for hardware controllers that use a serial port to connect. """

    def __init__(self, label: str = "serialController") -> None:
        super().__init__(label)
        #self.serial_dev_name = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        #self.serial_dev_name = "/tmp/ttyFAKE"
        self.serial_dev_name = "/dev/ttyUSB0"
        self.serial_baud = 115200
        self._serial = None
        self.testing: bool = False  # Prevent _periodic_io() from blocking during tests.
        self._serial_thread: Optional[threading.Thread] = None

    def connect(self) -> Literal[ConnectionState]:
        """ Try to open serial port. Set connection_status to CONNECTING. """
        print("connect")
        if self.connection_status in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connection_status

        self.set_connection_status(ConnectionState.CONNECTING)

        try:
            self._serial = serial.serial_for_url(
                self.serial_dev_name, self.serial_baud, timeout=0)
        except AttributeError:
            try:
                self._serial = serial.Serial(
                    self.serial_dev_name, self.serial_baud, timeout=0)
            except serial.serialutil.SerialException:
                self.set_connection_status(ConnectionState.MISSING_RESOURCE)
        except serial.serialutil.SerialException:
            self.set_connection_status(ConnectionState.MISSING_RESOURCE)

        return self.connection_status

    def disconnect(self) -> Literal[ConnectionState]:
        """ Close serial port, shut down serial port thread, etc.
        Set connection_status to DISCONNECTING.. """
        if self.connection_status in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connection_status
        if self.connection_status in [
                ConnectionState.CONNECTED,
                ConnectionState.CONNECTING]:
            print("Disconnecting %s %s" % (self.label, self.serial_dev_name))

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

        print("Connected %s %s" % (self.label, self.serial_dev_name))
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
        self._serial = None

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
                # Trying to diconnect.
                self.on_disconnected()

            elif self.connection_status in [
                    ConnectionState.FAIL, ConnectionState.MISSING_RESOURCE]:
                # A serial port error occurred either # while opening a serial port or
                # on an already open port.
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
