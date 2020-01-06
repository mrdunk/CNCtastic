from typing import List, Dict
from enum import Enum
import PySimpleGUI as sg

from terminals._terminalBase import _TerminalBase, diffDicts

className = "Gui"

class Gui(_TerminalBase):
    def __init__(self, layouts: List=[], label="gui"):
        super().__init__(label)
        self.setupDone: bool = False
        self.layout = []
        if layouts:
            self.setup(layouts)
        self._lastvalues: Dict = {}

    def setup(self, layouts: Dict):
        """ Since this component relies on data from many other components,
        we cannot do all the setup in __init__.
        Call this once layout data exists. """
        if self.setupDone:
            print("WARNING: Attempting to run setup() more than once on %s" %
                    self.label)
            return

        tabs = []
        for label, layout in layouts.items():
            tabs.append(sg.Tab(label, layout))

        self.layout = [[sg.TabGroup([tabs])]]

        self.window = sg.Window("CNCtastic", self.layout,
                                resizable=True, size=(600,600),
                                return_keyboard_events=True)
        self.setupDone: bool = True

        for event in self.window.AllKeysDict:
            self._subscriptions[event] = None

    def service(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        event, values = self.window.read(timeout=10)
        if event is None or values is None:
            print("Quitting via %s" % self.label)
            return False
        
        diffValues = diffDicts(self._lastvalues, values)
        self._lastvalues = values
        
        # Combine events with the values. Put the event key in there with empty value.
        if not event == "__TIMEOUT__":
            diffValues[event] = None
        
        if not event == "__TIMEOUT__" or diffValues:
            print(event, diffValues)

        for eventKey, value in diffValues.items():
            if isinstance(value, str):
                value = value.rstrip()
            self.publishOneByValue(eventKey, value)

        while self._delivered:
            event, value = self._delivered.popleft()
            if isinstance(value, Enum):
                self.window[event].update(value.name)
            else:
                self.window[event].update(value)

        return event not in (None, 'Exit')
    
    def close(self):
        self.window.close()

    def __del__(self):
        self.close()
