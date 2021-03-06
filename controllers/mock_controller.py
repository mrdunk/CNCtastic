""" Mock controller for use in unit-tests. """

from controllers.debug import DebugController
from definitions import ConnectionState

class MockController(DebugController):
    """ Mock controller for use in unit-tests. """

    # Set False as we don't want it to be used as a plugin.
    is_valid_plugin = False

    def early_update(self) -> bool:
        """ Called early in the event loop, before events have been received. """
        if self.connection_status == ConnectionState.CONNECTING:
            self.connection_status = ConnectionState.CONNECTED
        elif self.connection_status == ConnectionState.DISCONNECTING:
            self.connection_status = ConnectionState.NOT_CONNECTED

        if self.connection_status == ConnectionState.CONNECTED:
            self.ready_for_data = True
        else:
            self.ready_for_data = False

        return True
