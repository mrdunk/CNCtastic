from enum import Enum

import PySimpleGUI as sg

from coordinator.coordinator import Coordinator

def diffDicts(original, new):
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
            diff[key] = value

        return diff

class Gui:
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator

        tab1_layout = coordinator.activeController.guiLayout()
        
        tab2_layout = coordinator.interfaces["jogWidget"].guiLayout()

        tab3_layout = [[sg.T('This is inside tab 3')],
                       [sg.In(key='in2')]]

        self.layout = [[sg.TabGroup(
            [[  sg.Tab('Connect', tab1_layout),
                sg.Tab('Control', tab2_layout),
                sg.Tab('Gcode', tab3_layout),
            ]])],
            ]

        self.window = sg.Window("CNCtastic", self.layout, resizable=True, size=(600,600))

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
