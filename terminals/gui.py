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
        self._diffValues: Dict = {}
        self.description = "GUI interface."

    def setup(self, layouts: Dict):
        """ Since this component relies on data from many other components,
        we cannot do all the setup in __init__.
        Call this once layout data exists. """
        if self.setupDone:
            print("WARNING: Attempting to run setup() more than once on %s" %
                    self.label)
            return

        sg.SetOptions(element_padding=(1, 1))

        tabs = []
        for label, layout in layouts.items():
            tabs.append(sg.Tab(label, layout))

        self.layout = [[sg.TabGroup([tabs])]]

        self.window = sg.Window("CNCtastic", self.layout,
                                resizable=True, size=(600,600),
                                return_keyboard_events=True,
                                auto_size_text=False, auto_size_buttons=False,
                                default_element_size=(4, 2),
                                default_button_element_size=(4, 2)
                                )
        self.setupDone: bool = True

        # Subscribe to events matching GUI widget keys.
        for event in self.window.AllKeysDict:
            self._subscriptions[event] = None

    def earlyUpdate(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        if not self.setupDone:
            return

        event, values = self.window.read(timeout=10)
        if event is None or values is None:
            print("Quitting via %s" % self.label)
            return False
        
        self._diffValues = diffDicts(self._lastvalues, values)
        self._lastvalues = values
        
        # Combine events with the values. Put the event key in there with empty value.
        if not event == "__TIMEOUT__":
            self._diffValues[event] = None
        
        if not event == "__TIMEOUT__" or self._diffValues:
            print(event, self._diffValues)


        return event not in (None, ) and not event.startswith("Exit")
   
    def publish(self):
        for eventKey, value in self._diffValues.items():
            if isinstance(value, str):
                value = value.rstrip()
            self.publishOneByValue(eventKey, value)

    def receive(self):
        super().receive()
        
        # Since latency is important in the GUI, lets update the scree as soon
        # as possible after receiving the event.
        # This also helps with event loops when multiple things update a widget
        # that in turn sends an event.
        while self._delivered:
            event, value = self._delivered.popleft()
            if isinstance(value, Enum):
                self.window[event].update(value.name)
            else:
                self.window[event].update(value)

    def close(self):
        if not self.setupDone:
            return

        self.window.close()

    def __del__(self):
        self.close()
