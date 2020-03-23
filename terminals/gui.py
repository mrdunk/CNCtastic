""" Plugin to provide GUI using PySimpleGUI. """

from typing import List, Dict, Any, Type
from enum import Enum

# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
from PySimpleGUIQt_loader import sg

import common
from terminals._terminal_base import _TerminalBase, diff_dicts
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase


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
        self.layout: List[List[sg.Element]] = []
        self.selected_tab_key: str = ""
        self._lastvalues: Dict[str, Any] = {}
        self._diffvalues: Dict[str, Any] = {}
        self.description = "GUI interface."
        self.window: Any = None
        self.config: Dict[str, Any] = {}
        self.position = (1, 1)  # TODO: Make the window position persistent.
        self.size = (800, 600)

        self._setup_done: bool = False
        self._first_pass_done: bool = False

    def setup(self,
              interfaces: Dict[str, _InterfaceBase],
              controllers: Dict[str, _ControllerBase],
              controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        """ Since this component relies on data from many other components,
        we cannot do all the setup in __init__.
        Call this once layout data exists. """

        assert not self._setup_done, \
            "WARNING: Attempting to run setup() more than once on %s" % self.label

        super().setup(interfaces, controllers, controller_classes)

        sg.SetOptions(element_padding=(1, 1))
        #sg.theme("BlueMono")
        sg.theme("DarkGrey")

        if not self.sub_components:
            class_pages = common.load_plugins("gui_pages")
            self.sub_components = {page.label: page(interfaces, controllers, controller_classes)
                                   for _, page in class_pages}

        layouts = {}
        for key, value in {**self.interfaces,
                           **self.sub_components}.items():
            if hasattr(value, "gui_layout"):
                layouts[key] = value.gui_layout()

        tabs = []
        for label, layout in layouts.items():
            tabs.append(sg.Tab(label, layout, key="tabs_%s" % len(tabs)))

        self.layout = [[sg.TabGroup([tabs], key="tabs")]]

        self.window = sg.Window("CNCtastic",
                                self.layout,
                                resizable=True,
                                return_keyboard_events=True,
                                #auto_size_text=False,
                                #auto_size_buttons=False,
                                #default_element_size=(4, 2),
                                #default_button_element_size=(4, 2),
                                use_default_focus=False,
                                location=self.position,
                                size=self.size,
                                )
        self.window.Finalize()

        # Subscribe to events matching GUI widget keys.
        for event in self.window.AllKeysDict:
            self.event_subscriptions[event] = None

        self.event_subscriptions[self.key_gen("restart")] = ("_restart", None)
        self.event_subscriptions["__coordinator__:new_controller"] = ("_restart", None)

        self._setup_done = True
        self._first_pass_done = False

    def early_update(self) -> bool:
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

        if(event != "__TIMEOUT__" or self._diffvalues) and self.debug_show_events:
            print(event, self._diffvalues)

        self._publish_widgets()

        return event not in (None, ) and not event.startswith("Exit")

    def update(self) -> None:
        super().update()

        if not self._first_pass_done:
            self._first_pass_done = True
            self.publish(self.key_gen("has_restarted"), True)

            if self.selected_tab_key:
                self.window[self.selected_tab_key].select()

    def _publish_widgets(self) -> None:
        """ Publish all button presses and other GUI widget updates. """
        for event_, value in self._diffvalues.items():
            #if isinstance(value, str):
            #    value = value.strip()
            self.publish(event_, value)

    def receive(self) -> None:
        """ Receive events this object is subscribed to. """
        super().receive()

        # Since latency is important in the GUI, lets update the screen as soon
        # as possible after receiving the event.
        # This also helps with event loops when multiple things update a widget
        # that in turn sends an event.
        while self._delivered:
            event, value = self._delivered.popleft()

            if event in (self.key_gen("restart"), "__coordinator__:new_controller"):
                self._restart()
                continue

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

    def _restart(self) -> None:
        self.selected_tab_key = self.window["tabs"].get()
        #self.size = self.window.Size
        self.size = self.window.QT_QMainWindow.size().toTuple()
        #self.position = self.window.CurrentLocation()
        geom = self.window.QT_QMainWindow.frameGeometry()
        self.position = (geom.left(), geom.top())
        print("restart",
              self.position,
              self.size,
              self.selected_tab_key)
        self.close()
        self.setup(self.interfaces, self.controllers, self.controller_classes)

    def close(self) -> None:
        """ Close GUI window. """
        if not self._setup_done:
            return

        self._setup_done = False
        self.window.close()

    def __del__(self) -> None:
        self.close()
