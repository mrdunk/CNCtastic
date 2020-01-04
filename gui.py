from typing import Dict
from enum import Enum

import PySimpleGUI as sg

from coordinator.coordinator import Coordinator

def diffDicts(original: Dict, new: Dict) -> Dict:
    """ Compare 2 Dicts, returning any values that differ.
    It is presumed that the new Dict will contain all keys that are in the
    original Dict. The new Dict may have some keys that were not in the original.
    We also convert any numerical string values to floats as this is the most
    likely use.
    Args:
        original: A Dict to compare "new" against.
        new: A Dict of the expected values.
    Returns:
        A Dict of key:value pairs from "new" where either the key did not exist
            in "original" or the value differs. """
    diff = {}
    for key in new:

        # Values got from the GUI tend to be converted to strings.
        # Safest to presume they are floats.
        try:
            new[key] = float(new[key])
        except ValueError:
            pass

        value = new[key]
        if key in original:
            if value != original[key]:
                diff[key] = value
        else:
            # New key:value.
            # key did not exist in original.
            diff[key] = value

    return diff

class Gui:
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator

        allComponents = (
                list(coordinator.controllers.values()) +
                list(coordinator.interfaces.values()) +
                [coordinator])

        tabs = []
        for component in allComponents:
            if hasattr(component, "guiLayout"):
                componentLayout = component.guiLayout()
                if componentLayout:
                    tabs.append(sg.Tab(component.label, componentLayout))

        self.layout = [[sg.TabGroup([tabs])]]

        self.window = sg.Window("CNCtastic", self.layout,
                                resizable=True, size=(600,600),
                                return_keyboard_events=True)

        # Combine all the "exportToGui" methods in one place so we can iterate
        # through them quickly later.
        self.exports = {"coordinator": coordinator.exportToGui}
        for interface in coordinator.interfaces.values():
            if hasattr(interface, "exportToGui"):
                self.exports[interface.label] = getattr(interface, "exportToGui")
        if hasattr(coordinator.activeController, "exportToGui"):
            self.exports[coordinator.activeController.label] = \
                    getattr(coordinator.activeController, "exportToGui")

        self._lastvalues: Dict = {}

    def service(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        event, values = self.window.read(timeout=1000)
        if event is None or values is None:
            return False
        
        diffValues = diffDicts(self._lastvalues, values)
        self._lastvalues = values
        
        # Combine events with the values. Put the event key in there with empty value.
        if not event == "__TIMEOUT__":
            diffValues[event] = None
        
        if not event == "__TIMEOUT__" or diffValues:
            print(event, diffValues)

        self._sendEvents(diffValues)
        self._pollAllForGuiData()

        return event not in (None, 'Exit')

    def _sendEvents(self, diffValues):
        """ Send GUI events to all non GUI components. """
        for toUpdate in ([self.coordinator, self.coordinator.activeController] +
                list(self.coordinator.interfaces.values())):
            if hasattr(toUpdate, "performEvent"):
                toUpdate.performEvent(diffValues)

    def _pollAllForGuiData(self):
        """ Poll all components for data they wish to update the GUI. """
        for export in self.exports.values():
            d = export()
            for key, value in d.items():
                if key in self.window.AllKeysDict:
                    if isinstance(value, Enum):
                        self.window[key].update(value.name)
                    else:
                        self.window[key].update(value)


    def __del__(self):
        self.window.close()
