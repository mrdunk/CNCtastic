from typing import List
from gui_pages._page_base import _GuiPageBase
from terminals.gui import sg

class ControllerPicker(_GuiPageBase):
    is_valid_plugin = True

    label = "ControllerPicker"

    def gui_layout(self) -> List[List[List[sg.Element]]]:
        chooser_elements = []
        view_elements = []
        self.controller_widgets: Dict[str, sg.Frame] = {}
        self.controller_buttons: Dict[str, sg.Button] = {}

        # TODO: Make the enabled value persistent.
        enabled = list(self.controllers.keys())[0]

        for label, controller in self.controllers.items():
            self.event_subscriptions[self.key_gen("select_%s" % label)] = \
                ("_select_controller", label)

            if label == enabled:
                color = ("white ", "red")
                visible = True
            else:
                color = ("white ", "green")
                visible = False

            key = self.key_gen("select_%s" % label)
            button = sg.Button(label,
                               key=key,
                               size=(200, 40),
                               pad=(0, 0),
                               button_color=color)
            self.controller_buttons[key] = button
            chooser_elements.append([button])

            key = self.key_gen("view_%s" % label)
            widget = sg.Frame(label,
                              controller.gui_layout(),
                              key=key,
                              visible=visible,
                              )
            self.controller_widgets[key] = widget
            view_elements.append(widget)
        chooser = sg.Column(chooser_elements, pad=(0, 0))

        output = [
                [chooser] + view_elements,
                [sg.Button("Restart", size=(8, 2), key="gui:restart")],
            ]

        return output

    def _select_controller(self, event: str, label: str) -> None:
        self.publish_one_by_value("%s:active" % label, True)

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
