# Pylint seems to be looking at python2.7's PySimpleGUI libraries so we need the following:
# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" Send Gcode to active controller in response to GUI button presses. """

from typing import Dict, List, Union
from math import log10, floor

#import PySimpleGUIQt as sg
from terminals.gui import sg

from interfaces._interface_base import _InterfaceBase
from definitions import FlagState

def round_1_sf(number: float) -> float:
    """ Round a float to 1 significant figure. """
    return round(number, -int(floor(log10(abs(number)))))

class JogWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    def __init__(self, label: str = "jogWidget") -> None:
        super().__init__(label)

        self.label = label
        # Map incoming events to local member variables and callback methods.
        self.event_subscriptions = {
            self.key_gen("xyMultiply"): ("_xy_jog_step_multiply", 10),
            self.key_gen("xyDivide"): ("_xy_jog_step_multiply", 0.1),
            self.key_gen("xyJogStep"): ("_xy_jog_step", None),
            self.key_gen("zMultiply"): ("_z_jog_step_multiply", 10),
            self.key_gen("zDivide"): ("_z_jog_step_multiply", 0.1),
            self.key_gen("zJogStep"): ("_z_jog_step", None),
            self.key_gen("ul"): ("_move_handler", (-1, 1, 0)),
            self.key_gen("uc"): ("_move_handler", (0, 1, 0)),
            self.key_gen("ur"): ("_move_handler", (1, 1, 0)),
            self.key_gen("cl"): ("_move_handler", (-1, 0, 0)),
            self.key_gen("cr"): ("_move_handler", (1, 0, 0)),
            self.key_gen("dl"): ("_move_handler", (-1, -1, 0)),
            self.key_gen("dc"): ("_move_handler", (0, -1, 0)),
            self.key_gen("dr"): ("_move_handler", (1, -1, 0)),
            self.key_gen("uz"): ("_move_handler", (0, 0, 1)),
            self.key_gen("dz"): ("_move_handler", (0, 0, -1)),
            "active_controller:work_pos:x": ("_wpos_handler_x", None),
            "active_controller:work_pos:y": ("_wpos_handler_y", None),
            "active_controller:work_pos:z": ("_wpos_handler_z", None),
            self.key_gen("work_pos:x"): ("_wpos_handler_x_update", None),
            self.key_gen("work_pos:y"): ("_wpos_handler_y_update", None),
            self.key_gen("work_pos:z"): ("_wpos_handler_z_update", None),
            }

        self._xy_jog_step: float = 10
        self._z_jog_step: float = 10
        self._w_pos: Dict = {}

    def _xy_jog_step_multiply(self, multiplier: float) -> None:
        self._xy_jog_step = round_1_sf(self._xy_jog_step * multiplier)
        # Need to explicitly push this here as the GUI also sends an update with
        # the old value. This publish will take effect later.
        self.publish_one_by_value(self.key_gen("xyJogStep"), self._xy_jog_step)

    def _z_jog_step_multiply(self, multiplier: float) -> None:
        self._z_jog_step = round_1_sf(self._z_jog_step * multiplier)
        # Need to explicitly push this here as the GUI also sends an update with
        # the old value. This publish will take effect later.
        self.publish_one_by_value(self.key_gen("zJogStep"), self._z_jog_step)

    def _move_handler(self, values: List[int]) -> None:
        self.absolute_distance_mode(False)
        self.move_to(command="G00",
                     x=self._xy_jog_step * values[0],
                     y=self._xy_jog_step * values[1],
                     z=self._z_jog_step * values[2],
                     f=10000  # TODO: Feed rates on jog.py
                     )

    def _wpos_handler_x(self, value: float) -> None:
        """ Called in response to an active_controller:work_pos:x event. """
        self._w_pos["x"] = value
        self.publish_one_by_value(self.key_gen("work_pos:x"), value)

    def _wpos_handler_y(self, value: float) -> None:
        """ Called in response to an active_controller:work_pos:y event. """
        self._w_pos["y"] = value
        self.publish_one_by_value(self.key_gen("work_pos:y"), value)

    def _wpos_handler_z(self, value: float) -> None:
        """ Called in response to an active_controller:work_pos:z event. """
        self._w_pos["z"] = value
        self.publish_one_by_value(self.key_gen("work_pos:z"), value)

    def _wpos_handler_x_update(self, value: float) -> None:
        """ Called in response to a local :work_pos:x event. """
        try:
            float(value)
        except ValueError:
            return

        if "x" in self._w_pos and value == self._w_pos["x"]:
            # Nothing to do.
            return
        self._w_pos["x"] = value
        self.g92_offsets(**self._w_pos)

    def _wpos_handler_y_update(self, value: float) -> None:
        """ Called in response to a local :work_pos:y event. """
        try:
            float(value)
        except ValueError:
            return

        if "y" in self._w_pos and value == self._w_pos["y"]:
            # Nothing to do.
            return
        self._w_pos["y"] = value
        self.g92_offsets(**self._w_pos)

    def _wpos_handler_z_update(self, value: float) -> None:
        """ Called in response to a local :work_pos:z event. """
        try:
            float(value)
        except ValueError:
            return

        if "z" in self._w_pos and value == self._w_pos["z"]:
            # Nothing to do.
            return
        self._w_pos["z"] = value
        self.g92_offsets(**self._w_pos)

    def gui_layout(self) -> List:
        """ Layout information for the PySimpleGUI interface. """
        but_w = 5
        but_h = 1.5
        def txt(label: str, but_w: float = but_w, but_h: float = but_h) -> sg.Frame:
            """ Text output. """
            return sg.Text(
                label, justification="center", size=(but_w, but_h),
                #background_color="grey"
                )

        def but(label: str, key: str) -> sg.Button:
            """ Square button. """
            return sg.Button(label, key=self.key_gen(key), size=(but_w, but_h))

        def drp(key: str) -> sg.Drop:
            """ Drop down chooser for feed rates. """
            drop = sg.Drop(key=self.key_gen(key),
                           #enable_events=False,
                           values=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
                           default_value=self._xy_jog_step, size=(but_w, 1))
            return drop

        coord_w: float = 10
        coord_h: float = 1
        def w_coord(key: str) -> sg.InputText:
            """ Text field for workspace coordinate positions. """
            return sg.InputText(key,
                                key=self.key_gen(key),
                                size=(coord_w, coord_h),
                                justification="right",
                                pad=(0, 0),
                                #background_color="grey",
                                )

        def m_coord(key: str) -> sg.InputText:
            """ Text field for machine coordinate positions. (Not updatable) """
            return sg.InputText(key,
                                key="active_controller:%s" % key,
                                size=(coord_w, coord_h),
                                justification="right",
                                pad=(0, 0),
                                disabled=True,
                                background_color="grey",
                                )

        def f_coord(key: str) -> sg.InputText:
            """ Text field for feed rate coordinate values. (Not updatable) """
            return sg.InputText(key,
                                key="active_controller:%s" % key,
                                size=(coord_w / 2, coord_h),
                                justification="right",
                                pad=(0, 0),
                                disabled=True,
                                background_color="grey",
                                )

        pos = [
            [txt("machine_pos:", coord_w, coord_h),
             m_coord("machine_pos:x"),
             m_coord("machine_pos:y"),
             m_coord("machine_pos:z")],
            [txt("work_pos:", coord_w, coord_h),
             w_coord("work_pos:x"),
             w_coord("work_pos:y"),
             w_coord("work_pos:z")],
            ]
        feed = [
            [txt("Max feed:", coord_w, coord_h),
             f_coord("feed_rate_max:x"),
             f_coord("feed_rate_max:y"),
             f_coord("feed_rate_max:z")],
            [txt("Feed accel:", coord_w, coord_h),
             f_coord("feed_rate_accel:x"),
             f_coord("feed_rate_accel:y"),
             f_coord("feed_rate_accel:z")],
            [txt("Current feed:", coord_w, coord_h),
             f_coord("feed_rate")]
            ]


        layout_xy = [
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt(""),  txt(""),        txt("Y"),       txt("")],
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt(""),  but("", "ul"),  but("^", "uc"), but("", "ur")],
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt("X"), but("<", "cl"), but("0", "cc"), but(">", "cr")],
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt(""),  but("", "dl"),  but("v", "dc"), but("", "dr")],
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt("")],
            # pylint: disable=C0326  # Exactly one space required after comma
            [txt(""),  but("/10","xyDivide"), drp("xyJogStep"), but("x10", "xyMultiply")],
            ]
        layout_z = [
            [txt(""), txt("Z")],
            [txt(""), but("^", "uz")],
            [txt(""), but("0", "cz")],
            [txt(""), but("v", "dz")],
            [txt("")],
            [but("/10", "zDivide"), drp("zJogStep"), but("x10", "zMultiply")],
            ]

        layout = [
            [sg.Column(pos),
             sg.Column(feed),
             sg.Stretch()
             ],
            [sg.Column(layout_xy, pad=(0, 0), size=(1, 1)),
             sg.Column(layout_z, pad=(0, 0), size=(1, 1)),
             sg.Stretch()
             ]
            ]
        return layout

    def move_to(self, **argkv: Union[float, str]) -> None:
        """ Move the machine head.
        Args:
            argkv: A dict containing one or more of the following parameters:
                command: The gcode command as a string. Defaults to "G01".
                x: The x coordinate.
                y: The y coordinate.
                z: The z coordinate.
                f: The feed rate.
        """
        super().move_to(**argkv)
        self._updated_data.jog = FlagState.TRUE
