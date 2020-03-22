from typing import List, Dict, Type, Any
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase
from gui_pages._page_base import _GuiPageBase
from terminals.gui import sg

class ControllerPicker(_GuiPageBase):
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

    def _button(self, label: str) -> sg.Button:
        key = self.key_gen("select_%s" % label)
        self.event_subscriptions[key] = ("_select_controller", label)

        if label == self.enabled:
            color = ("white ", "red")
            visible = True
        else:
            color = ("white ", "green")
            visible = False

        button = sg.Button(label,
                           key=key,
                           size=(200, 40),
                           pad=(0, 0),
                           button_color=color)
        self.controller_buttons[key] = button

        return button

    def _configure_widget(self, label: str, controller) -> sg.Frame:
        if label == self.enabled:
            visible = True
        else:
            visible = False

        key = self.key_gen("view_%s" % label)
        widget = sg.Frame(label,
                          controller.gui_layout(),
                          key=key,
                          visible=visible,
                          )
        self.controller_widgets[key] = widget

        return widget

    def _new_widget(self) -> sg.Frame:
        if "##new_controller" == self.enabled:
            visible = True
        else:
            visible = False

        layout = []
        for label, controller_class in self.controller_classes.items():
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

        chooser = sg.Column(chooser_elements, pad=(0, 0))

        output = [
                [chooser] + view_elements,
                [sg.Button("Restart", size=(8, 2), key="gui:restart")],
            ]
        return output

    def _select_controller(self, event: str, label: str) -> None:
        self.publish("%s:active" % label, True)
        self.enabled = label

        widget_key = self.key_gen("view_%s" % label)
        for key, widget in self.controller_widgets.items():
            if widget_key == key:
                widget.Update(visible=True)
            else:
                widget.Update(visible=False)

        button_key = self.key_gen("select_%s" % label)
        for key, button in self.controller_buttons.items():
            if button_key == key:
                button.Update(button_color=("white ", "red"))
            else:
                button.Update(button_color=("white ", "green"))

    def _new_controller(self, event: str, label: str) -> None:
        self.enabled = "new"
        self.publish("gui:request_new_controller", label)

    def redraw(self, event: str="", value: Any=None) -> None:
        for label, controller in self.controllers.items():
            controller.sync()

