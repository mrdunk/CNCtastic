import serial
import threading


from controllers._controllerBase import _ControllerBase
from definitions import ConnectionState

SERIAL_INTERVAL = 0.02 # seconds


class _SerialControllerBase(_ControllerBase):
    def __init__(self, label: str="serialController"):
        super().__init__(label)
        #self.serialDevName = "spy:///tmp/ttyFAKE?file=/tmp/serialspy.txt"
        self.serialDevName = "/tmp/ttyFAKE"
        self.serialBaud = 115200
        self._serial = None
        self.testing: bool = False  # Prevent _periodicIO() from blocking during tests.
    
    def connect(self):
        """ Try to open serial port. Set connectionStatus to CONNECTING. """
        print("connect")
        if self.connectionStatus in [
                ConnectionState.CONNECTING,
                ConnectionState.CONNECTED,
                ConnectionState.MISSING_RESOURCE]:
            return self.connectionStatus

        self.setConnectionStatus(ConnectionState.CONNECTING)
        
        try:
            self._serial = serial.serial_for_url(
                    self.serialDevName, self.serialBaud, timeout=0)
        except AttributeError:
            try:
                self._serial = serial.Serial(
                        self.serialDevName, self.serialBaud, timeout=0)
            except serial.serialutil.SerialException:
                self.setConnectionStatus(ConnectionState.MISSING_RESOURCE)
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.MISSING_RESOURCE)

        return self.connectionStatus

    def disconnect(self) :
        """ Close serial port, shut down serial port thread, etc.
        Set connectionStatus to DISCONNECTING.. """
        print("Disconnecting %s %s" % (self.label, self.serialDevName))
        if self.connectionStatus in [
                ConnectionState.DISCONNECTING,
                ConnectionState.NOT_CONNECTED]:
            return self.connectionStatus

        if self._serial is None:
            self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        else:
            self.setConnectionStatus(ConnectionState.DISCONNECTING)

            self._serialThread.join()
            self._serial.close()

        self.readyForData = False
        
        return self.connectionStatus

    def onConnected(self):
        """ Executed when serial port first comes up.
        Check serial port is open then start serial port thread.
        Set connectionStatus to CONNECTED. """
        if not self._serial.is_open:
            return

        print("Connected %s %s" % (self.label, self.serialDevName))
        self.setConnectionStatus(ConnectionState.CONNECTED)

        # Drain the buffer of any noise.
        self._serial.flush()
        while self._serial.readline():
            pass

        self._serialThread = threading.Thread(target=self._periodicIO)
        self._serialThread.daemon = True
        self._serialThread.start()

    def onDisconnected(self):
        """ Executed when serial port is confirmed closed.
        Check serial port was closed then set connectionStatus to NOT_CONNECTED. """
        if self._serial.is_open:
            return

        print("Serial disconnected.")
        self.setConnectionStatus(ConnectionState.NOT_CONNECTED)
        self._serial = None

    def _serialWrite(self, data) -> bool:
        """ Send data to serial port. """
        try:
            self._serial.write(data)
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.FAIL)
            return False
        return True

    def _serialRead(self) -> bytes:
        """ Read data from serial port. """
        try:
            if not self._serial.inWaiting():
                return b""
        except OSError:
            self.setConnectionStatus(ConnectionState.FAIL)

        line = None
        try:
            line = self._serial.readline()
        except serial.serialutil.SerialException:
            self.setConnectionStatus(ConnectionState.FAIL)
        return line

    def earlyUpdate(self):
        """ Called early in the event loop, before events have been received. """
        if self.connectionStatus != self.desiredConnectionStatus:
            # Transition between connection states.
            if self.connectionStatus is ConnectionState.CONNECTING:
                # Connection process already started.
                self.onConnected()

            elif self.connectionStatus is ConnectionState.DISCONNECTING:
                # Trying to diconnect.
                self.onDisconnected()

            elif self.connectionStatus in [
                    ConnectionState.FAIL, ConnectionState.MISSING_RESOURCE]:
                # A serial port error occurred either # while opening a serial port or
                # on an already open port.
                self.setDesiredConnectionStatus(ConnectionState.NOT_CONNECTED)
                self.setConnectionStatus(ConnectionState.CLEANUP)

            elif self.desiredConnectionStatus is ConnectionState.CONNECTED:
                # Start connection process.
                self.connect()

            elif self.desiredConnectionStatus is ConnectionState.NOT_CONNECTED:
                # Start disconnection.
                self.disconnect()
        
    def _periodicIO(self):
        """ Read from and write to serial port.
            Called from a separate thread.
            Blocks while serial port remains connected. """
        while self.connectionStatus is ConnectionState.CONNECTED:
            print("do read and write here.")

            self._time.sleep(SERIAL_INTERVAL)

            if self.testing:
                break

