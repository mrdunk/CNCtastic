""" Plugin to provide GUI using PySimpleGUI. """

from typing import List, Dict, Any
from enum import Enum

import PySimpleGUIQt as sg
#import PySimpleGUIWeb as sg

from terminals._terminal_base import _TerminalBase, diff_dicts

class Gui(_TerminalBase):
    """ Display GUI interface.
    Will display the widgets in any other component loaded as a plugin's "layout"
    property. See the "JogWidget" component as an example. """

    # Active unless disabled with flag at runtime.
    active_by_default = True

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    def __init__(self, label: str = "gui") -> None:
        super().__init__(label)
        self._setup_done: bool = False
        self.layout: List[List[sg.Element]] = []
        self._lastvalues: Dict[str, Any] = {}
        self._diffvalues: Dict[str, Any] = {}
        self.description = "GUI interface."
        self.window: Any = None

    def setup(self, layouts: Dict[str, List[List[sg.Element]]]) -> None:  # type: ignore[override]
        """ Since this component relies on data from many other components,
        we cannot do all the setup in __init__.
        Call this once layout data exists. """
        if self._setup_done:
            print("WARNING: Attempting to run setup() more than once on %s" %
                  self.label)
            return

        sg.SetOptions(element_padding=(1, 1))

        tabs = []
        for label, layout in layouts.items():
            tabs.append(sg.Tab(label, layout))

        self.layout = [[sg.TabGroup([tabs])]]

        self.window = sg.Window("CNCtastic", self.layout,
                                resizable=True, size=(600, 600),
                                return_keyboard_events=True,
                                auto_size_text=False, auto_size_buttons=False,
                                default_element_size=(4, 2),
                                default_button_element_size=(4, 2),
                                use_default_focus=False,
                                )
        self._setup_done = True

        # Subscribe to events matching GUI widget keys.
        for event in self.window.AllKeysDict:
            self.event_subscriptions[event] = None

        #print(self.window.FindElement('canvas').TKCanvas)

    def early_update(self) -> bool:  # type: ignore[override]
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        if not self._setup_done:
            return False

        event, values = self.window.read(timeout=10)
        if event is None or values is None:
            print("Quitting via %s" % self.label)
            return False

        self._diffvalues = diff_dicts(self._lastvalues, values)
        self._lastvalues = values

        # Combine events with the values. Put the event key in there with empty value.
        if not event == "__TIMEOUT__":
            key_value = None
            if len(event) == 1 or event.startswith("special "):
                # This is a key-press of a regular "qwerty" key.
                key_value = event
                event = "gui:keypress"

            if event not in self._diffvalues:
                self._diffvalues[event] = key_value or None

        if(not event == "__TIMEOUT__" or self._diffvalues) and self.debug_show_events:
            print(event, self._diffvalues)

        return event not in (None, ) and not event.startswith("Exit")

    def publish(self) -> None:  # pylint: disable=W0221  # Un-needed arguments.
        """ Publish all events listed in the self.events_to_publish collection. """
        for event_, value in self._diffvalues.items():
            #if isinstance(value, str):
            #    value = value.strip()
            self.publish_one_by_value(event_, value)

    def receive(self) -> None:
        """ Receive events this object is subscribed to. """
        super().receive()

        # Since latency is important in the GUI, lets update the screen as soon
        # as possible after receiving the event.
        # This also helps with event loops when multiple things update a widget
        # that in turn sends an event.
        while self._delivered:
            event, value = self._delivered.popleft()
            if(hasattr(self.window[event], "metadata") and
               self.window[event].metadata and
               self.window[event].metadata.get("skip_update", False)):
                # GUI widget has "skip_update" set so will not use the default
                # update method.
                continue
            if isinstance(value, Enum):
                self.window[event].update(value.name)
            elif isinstance(value, float):
                if int(value) == value:
                    value = int(value)
                self.window[event].update(value)
            else:
                try:
                    self.window[event].update(value)
                except AttributeError:
                    # Some PySimpleGUI element types can't be updates until they
                    # have been populated with data. eg: the "Graph" element in
                    # PySimpleGUIQt.
                    pass

    def close(self) -> None:
        """ Close GUI window. """
        if not self._setup_done:
            return

        self.window.close()

    def __del__(self) -> None:
        self.close()
