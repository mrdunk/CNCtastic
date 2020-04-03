""" A GUI page for selecting and configuring controllers. """

from typing import List, Dict, Type, Any
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase
from gui_pages._page_base import _GuiPageBase

# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
from PySimpleGUIQt_loader import sg

class ControllerPicker(_GuiPageBase):
    """ A GUI page for selecting and configuring controllers. """
    is_valid_plugin = True

    label = "ControllerPicker"

    def __init__(self,
                 interfaces: Dict[str, _InterfaceBase],
                 controllers: Dict[str, _ControllerBase],
                 controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        super().__init__(interfaces, controllers, controller_classes)
        self.controller_widgets: Dict[str, sg.Frame] = {}
        self.controller_buttons: Dict[str, sg.Button] = {}
        self.enabled: str = ""

        # Repopulate GUI fields after a GUI restart.
        self.event_subscriptions["gui:has_restarted"] = ("redraw", None)
        for controller in self.controllers:
            self.event_subscriptions["%s:active" % controller] = \
                ("_on_activated_controller", controller)
        self.event_subscriptions["__coordinator__:new_controller"] = \
                ("_on_new_controller", None)
        self.event_subscriptions["##new_controller:picker"] = \
                ("_on_activated_controller", "##new_controller")


    def _button(self, label: str) -> sg.Button:
        """ Return a button widget for selecting which controller is selected. """
        key = "%s:active_buttonpress" % label
        self.event_subscriptions[key] = ("_on_button_press", label)

        if label == self.enabled:
            color = ("white ", "red")
        else:
            color = ("white ", "green")

        button = sg.Button(label,
                           key=key,
                           size=(150, 30),
                           pad=(0, 0),
                           button_color=color)
        self.controller_buttons[key] = button

        return button

    def _on_button_press(self, event_name: str, controller_label: str) -> None:
        """ Called in response to `_button()` press."""
        if controller_label == "##new_controller":
            self._on_activated_controller(event_name, controller_label)
            return

        self.publish("%s:set_active" % controller_label, True)

    def _configure_widget(self, label: str, controller: _ControllerBase) -> sg.Frame:
        """ Return a widget for configuring a controller. """
        visible = bool(label == self.enabled)

        key = self.key_gen("view_%s" % label)
        widget = sg.Frame(label,
                          controller.gui_layout(),
                          key=key,
                          visible=visible,
                          )
        self.controller_widgets[key] = widget

        return widget

    def _new_widget(self) -> sg.Frame:
        """ Return a widget for selecting what type of new controller is wanted. """
        visible = bool(self.enabled == "##new_controller")

        layout = []
        for label in self.controller_classes:
            key = self.key_gen("new_controller__%s" % label)
            self.event_subscriptions[key] = ("_new_controller", label)
            button = sg.Button(label, key=key,)
            layout.append([button])

        widget = sg.Frame("New controller",
                          layout,
                          visible=visible,)
        key = self.key_gen("view_##new_controller")
        self.controller_widgets[key] = widget
        return widget

    def gui_layout(self) -> List[List[List[sg.Element]]]:
        """ Return the GUI page with sections for all controllers. """
        chooser_elements = []
        view_elements = []
        self.controller_widgets = {}
        self.controller_buttons = {}

        # TODO: Make the enabled value persistent.
        if not self.enabled:
            self.enabled = list(self.controllers.keys())[0]

        for label, controller in self.controllers.items():
            button = self._button(label)
            chooser_elements.append([button])

            widget = self._configure_widget(label, controller)
            view_elements.append(widget)

        button = self._button("##new_controller")
        chooser_elements.append([button])
        widget = self._new_widget()
        view_elements.append(widget)

        chooser = sg.Column(chooser_elements, pad=(0, 0), background_color="grey")

        output = [
            [chooser] + view_elements,
            [sg.Button("Restart", size=(8, 2), key="gui:restart")],
            ]
        return output

    def _on_activated_controller(self, event_name: str, event_value: str) -> None:
        """ Display GUI for a particular controller. """
        #print("gui_pages._on_activated_controller", event_name, event_value)
        if not event_value:
            return
        label = event_name.split(":", 1)[0]

        self.enabled = label

        widget_key = self.key_gen("view_%s" % label)
        for key, widget in self.controller_widgets.items():
            if widget_key == key:
                widget.Update(visible=True)
            else:
                widget.Update(visible=False)

        button_key = "%s:active_buttonpress" % label
        for key, button in self.controller_buttons.items():
            if button_key == key:
                button.Update(button_color=("white ", "red"))
            else:
                button.Update(button_color=("white ", "green"))

        self.publish("gui:set_tab", self.label)

    def redraw(self, _: str = "", __: Any = None) -> None:
        """ Publish events of all controller parameters to re-populate page. """
        for controller in self.controllers.values():
            controller.sync()

    def _new_controller(self, _: str, label: str) -> None:
        """ Delegate creating a new controller to the coordinator. """
        self.enabled = "new"
        self.publish("request_new_controller", label)

    def _on_new_controller(self, _: str, label: str) -> None:
        """ Response to a __coordinator__:new_controller event. """

        self.event_subscriptions["%s:active" % label] = \
            ("_on_activated_controller", label)
