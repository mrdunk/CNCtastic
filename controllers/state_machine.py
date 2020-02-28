""" State machines reflecting the state of hardware controllers.
Typically each hardware controller type will have it's own SM class inheriting
from StateMachineBase. """

from typing import Dict, List, Callable, Optional, Any

from definitions import MODAL_GROUPS, MODAL_COMMANDS


def keys_to_lower(dict_: Dict[str, Any]) -> Dict[str, Any]:
    """ Translate a dict's keys to lower case. """
    return {k.lower(): v for k, v in dict_.items()}

class StateMachineBase:
    """ Base class for State Machines reflecting the state of hardware controllers. """

    machine_properties = [
        "machine_pos",
        "machine_pos_max",
        "machine_pos_min",
        "work_pos",
        "work_offset",
        "feed_rate",
        "feed_rate_max",
        "feed_rate_accel",
        #"feed_override",
        #"rapid_override",
        "spindle_rate",
        "spindle_override",
        "limit_x",
        "limit_y",
        "limit_z",
        "limit_a",
        "limit_b",
        "probe",
        "pause",
        "pause_park",        # Gracefully parking head after a pause event.
        "parking",
        "halt",
        "door",
        ]

    # Cheaper than global lookups
    MODAL_GROUPS: Dict[str, Dict[str, Any]] = MODAL_GROUPS
    MODAL_COMMANDS = MODAL_COMMANDS

    def __init__(self, on_update_callback: Callable[[str, Any], None]) -> None:
        self.on_update_callback = on_update_callback

        self.__machine_pos: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machine_pos_max: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__machine_pos_min: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__work_pos: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__work_offset: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feed_rate: float = 0
        self.__feed_rate_max: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feed_rate_accel: Dict[str, float] = {"x": 0, "y": 0, "z": 0, "a": 0, "b": 0}
        self.__feed_override: float = 100
        self.__rapid_override: float = 100
        self.__spindle_rate: float = 0
        self.__spindle_override: int = 100
        self.__limit_x: float = False
        self.__limit_y: float = False
        self.__limit_z: float = False
        self.__limit_a: float = False
        self.__limit_b: float = False
        self.__probe: bool = False
        self.__pause: bool = False
        self.pause_reason: List[str] = []
        self.__pause_park: bool = False
        self.__parking: bool = False
        self.__halt: bool = False
        self.halt_reason: List[str] = []
        self.__door: bool = False

        self.gcode_modal: Dict[bytes, bytes] = {}

        self.version: List[str] = []  # Up to the controller how this is populated.
        self.machine_identifier: List[str] = []  # Up to the controller how this is populated.

        self.changes_made: bool = True

    def __str__(self) -> str:
        output = ("Pause: {self.pause}\tHalt: {self.halt}\n")
        output += ("machine_pos x: {self.machine_pos[x]} y: {self.machine_pos[y]} "
                   "z: {self.machine_pos[z]} a: {self.machine_pos[a]} "
                   "b: {self.machine_pos[b]}\r\n")
        if self.machine_pos != self.work_pos:
            output += ("work_pos x: {self.work_pos[x]} y: {self.work_pos[y]} "
                       "z: {self.work_pos[z]} a: {self.work_pos[a]} "
                       "b: {self.work_pos[b]}\r\n")
            output += ("work_offset x: {self.work_offset[x]} y: {self.work_offset[y]} "
                       "z: {self.work_offset[z]} a: {self.work_offset[a]} "
                       "b: {self.work_offset[b]}\r\n")
        output += "feed_rate: {self.feed_rate}\r\n"
        output += "gcode_modalGroups: {self.gcode_modal}\r\n"
        return output.format(self=self)

    def sync(self) -> None:
        """ Publish all machine properties. """
        for prop in self.machine_properties:
            value = getattr(self, prop)

            # Publish whole property.
            self.on_update_callback(prop, value)

            # Also publish component parts if property is a dict.
            if isinstance(value, dict):
                for sub_prop, sub_value in value.items():
                    self.on_update_callback("%s:%s" % (prop, sub_prop), sub_value)

    @property
    def work_offset(self) -> Dict[str, float]:
        """ Getter. """
        return self.__work_offset

    @work_offset.setter
    def work_offset(self, pos: Dict[str, float]) -> None:
        """ Setter. """
        pos = keys_to_lower(pos)
        data_changed = False
        pos_x = pos.get("x")
        pos_y = pos.get("y")
        pos_z = pos.get("z")
        pos_a = pos.get("a")
        pos_b = pos.get("b")
        if pos_x is not None:
            if self.__work_offset["x"] != pos_x:
                data_changed = True
                self.__work_offset["x"] = pos_x
                self.__work_pos["x"] = self.machine_pos["x"] - pos_x
        if pos_y is not None:
            if self.__work_offset["y"] != pos_y:
                data_changed = True
                self.__work_offset["y"] = pos_y
                self.__work_pos["y"] = self.machine_pos["y"] - pos_y
        if pos_z is not None:
            if self.__work_offset["z"] != pos_z:
                data_changed = True
                self.__work_offset["z"] = pos_z
                self.__work_pos["z"] = self.machine_pos["z"] - pos_z
        if pos_a is not None:
            if self.__work_offset["a"] != pos_a:
                data_changed = True
                self.__work_offset["a"] = pos_a
                self.__work_pos["a"] = self.machine_pos["a"] - pos_a
        if pos_b is not None:
            if self.__work_offset["b"] != pos_b:
                data_changed = True
                self.__work_offset["b"] = pos_b
                self.__work_pos["b"] = self.machine_pos["b"] - pos_b

        if data_changed:
            self.on_update_callback("work_offset:x", self.work_offset["x"])
            self.on_update_callback("work_offset:y", self.work_offset["y"])
            self.on_update_callback("work_offset:z", self.work_offset["z"])
            self.on_update_callback("work_offset:a", self.work_offset["a"])
            self.on_update_callback("work_offset:b", self.work_offset["b"])
            self.on_update_callback("work_offset", self.work_offset)
            self.on_update_callback("work_pos:x", self.work_pos["x"])
            self.on_update_callback("work_pos:y", self.work_pos["y"])
            self.on_update_callback("work_pos:z", self.work_pos["z"])
            self.on_update_callback("work_pos:a", self.work_pos["a"])
            self.on_update_callback("work_pos:b", self.work_pos["b"])
            self.on_update_callback("work_pos", self.work_pos)

    @property
    def machine_pos_max(self) -> Dict[str, float]:
        """ Getter. """
        return self.__machine_pos_max

    @machine_pos_max.setter
    def machine_pos_max(self, pos: Dict[str, float]) -> None:
        """ Setter. """
        pos = keys_to_lower(pos)
        data_changed = False
        pos_x = pos.get("x")
        pos_y = pos.get("y")
        pos_z = pos.get("z")
        pos_a = pos.get("a")
        pos_b = pos.get("b")
        if pos_x is not None:
            if self.machine_pos_max["x"] != pos_x:
                data_changed = True
                self.machine_pos_max["x"] = pos_x
        if pos_y is not None:
            if self.machine_pos_max["y"] != pos_y:
                data_changed = True
                self.machine_pos_max["y"] = pos_y
        if pos_z is not None:
            if self.machine_pos_max["z"] != pos_z:
                data_changed = True
                self.machine_pos_max["z"] = pos_z
        if pos_a is not None:
            if self.machine_pos_max["a"] != pos_a:
                data_changed = True
                self.machine_pos_max["a"] = pos_a
        if pos_b is not None:
            if self.machine_pos_max["b"] != pos_b:
                data_changed = True
                self.machine_pos_max["b"] = pos_b

        if data_changed:
            self.on_update_callback("machine_pos_max:x", self.machine_pos_max["x"])
            self.on_update_callback("machine_pos_max:y", self.machine_pos_max["y"])
            self.on_update_callback("machine_pos_max:z", self.machine_pos_max["z"])
            self.on_update_callback("machine_pos_max:a", self.machine_pos_max["a"])
            self.on_update_callback("machine_pos_max:b", self.machine_pos_max["b"])
            self.on_update_callback("machine_pos_max", self.machine_pos_max)

    @property
    def machine_pos_min(self) -> Dict[str, float]:
        """ Getter. """
        return self.__machine_pos_min

    @machine_pos_min.setter
    def machine_pos_min(self, pos: Dict[str, float]) -> None:
        """ Setter. """
        pos = keys_to_lower(pos)
        data_changed = False
        pos_x = pos.get("x")
        pos_y = pos.get("y")
        pos_z = pos.get("z")
        pos_a = pos.get("a")
        pos_b = pos.get("b")
        if pos_x is not None:
            if self.machine_pos_min["x"] != pos_x:
                data_changed = True
                self.machine_pos_min["x"] = pos_x
        if pos_y is not None:
            if self.machine_pos_min["y"] != pos_y:
                data_changed = True
                self.machine_pos_min["y"] = pos_y
        if pos_z is not None:
            if self.machine_pos_min["z"] != pos_z:
                data_changed = True
                self.machine_pos_min["z"] = pos_z
        if pos_a is not None:
            if self.machine_pos_min["a"] != pos_a:
                data_changed = True
                self.machine_pos_min["a"] = pos_a
        if pos_b is not None:
            if self.machine_pos_min["b"] != pos_b:
                data_changed = True
                self.machine_pos_min["b"] = pos_b

        if data_changed:
            self.on_update_callback("machine_pos_min:x", self.machine_pos_min["x"])
            self.on_update_callback("machine_pos_min:y", self.machine_pos_min["y"])
            self.on_update_callback("machine_pos_min:z", self.machine_pos_min["z"])
            self.on_update_callback("machine_pos_min:a", self.machine_pos_min["a"])
            self.on_update_callback("machine_pos_min:b", self.machine_pos_min["b"])
            self.on_update_callback("machine_pos_min", self.machine_pos_min)

    @property
    def machine_pos(self) -> Dict[str, float]:
        """ Getter. """
        return self.__machine_pos

    @machine_pos.setter
    def machine_pos(self, pos: Dict[str, float]) -> None:
        """ Setter. """
        pos = keys_to_lower(pos)
        data_changed = False
        pos_x = pos.get("x")
        pos_y = pos.get("y")
        pos_z = pos.get("z")
        pos_a = pos.get("a")
        pos_b = pos.get("b")
        if pos_x is not None:
            if self.machine_pos["x"] != pos_x:
                data_changed = True
                self.machine_pos["x"] = pos_x
                self.work_pos["x"] = pos_x - self.work_offset.get("x", 0)
        if pos_y is not None:
            if self.machine_pos["y"] != pos_y:
                data_changed = True
                self.machine_pos["y"] = pos_y
                self.work_pos["y"] = pos_y - self.work_offset.get("y", 0)
        if pos_z is not None:
            if self.machine_pos["z"] != pos_z:
                data_changed = True
                self.machine_pos["z"] = pos_z
                self.work_pos["z"] = pos_z - self.work_offset.get("z", 0)
        if pos_a is not None:
            if self.machine_pos["a"] != pos_a:
                data_changed = True
                self.machine_pos["a"] = pos_a
                self.work_pos["a"] = pos_a - self.work_offset.get("a", 0)
        if pos_b is not None:
            if self.machine_pos["b"] != pos_b:
                data_changed = True
                self.machine_pos["b"] = pos_b
                self.work_pos["b"] = pos_b - self.work_offset.get("b", 0)

        if data_changed:
            self.on_update_callback("machine_pos:x", self.machine_pos["x"])
            self.on_update_callback("machine_pos:y", self.machine_pos["y"])
            self.on_update_callback("machine_pos:z", self.machine_pos["z"])
            self.on_update_callback("machine_pos:a", self.machine_pos["a"])
            self.on_update_callback("machine_pos:b", self.machine_pos["b"])
            self.on_update_callback("machine_pos", self.machine_pos)
            self.on_update_callback("work_pos:x", self.work_pos["x"])
            self.on_update_callback("work_pos:y", self.work_pos["y"])
            self.on_update_callback("work_pos:z", self.work_pos["z"])
            self.on_update_callback("work_pos:a", self.work_pos["a"])
            self.on_update_callback("work_pos:b", self.work_pos["b"])
            self.on_update_callback("work_pos", self.work_pos)

    @property
    def work_pos(self) -> Dict[str, float]:
        """ Getter. """
        return self.__work_pos

    @work_pos.setter
    def work_pos(self, pos: Dict[str, float]) -> None:
        """ Setter. """
        pos = keys_to_lower(pos)
        data_changed = False
        pos_x = pos.get("x")
        pos_y = pos.get("y")
        pos_z = pos.get("z")
        pos_a = pos.get("a")
        pos_b = pos.get("b")
        if pos_x is not None:
            if self.work_pos["x"] != pos_x:
                data_changed = True
                self.work_pos["x"] = pos_x
                self.machine_pos["x"] = pos_x + self.__work_offset.get("x", 0)
        if pos_y is not None:
            if self.work_pos["y"] != pos_y:
                data_changed = True
                self.work_pos["y"] = pos_y
                self.machine_pos["y"] = pos_y + self.__work_offset.get("y", 0)
        if pos_z is not None:
            if self.work_pos["z"] != pos_z:
                data_changed = True
                self.work_pos["z"] = pos_z
                self.machine_pos["z"] = pos_z + self.__work_offset.get("z", 0)
        if pos_a is not None:
            if self.work_pos["a"] != pos_a:
                data_changed = True
                self.work_pos["a"] = pos_a
                self.machine_pos["a"] = pos_a + self.__work_offset.get("a", 0)
        if pos_b is not None:
            if self.work_pos["b"] != pos_b:
                data_changed = True
                self.work_pos["b"] = pos_b
                self.machine_pos["b"] = pos_b + self.__work_offset.get("b", 0)

        if data_changed:
            self.on_update_callback("machine_pos:x", self.machine_pos["x"])
            self.on_update_callback("machine_pos:y", self.machine_pos["y"])
            self.on_update_callback("machine_pos:z", self.machine_pos["z"])
            self.on_update_callback("machine_pos:a", self.machine_pos["a"])
            self.on_update_callback("machine_pos:b", self.machine_pos["b"])
            self.on_update_callback("machine_pos", self.machine_pos)
            self.on_update_callback("work_pos:x", self.work_pos["x"])
            self.on_update_callback("work_pos:y", self.work_pos["y"])
            self.on_update_callback("work_pos:z", self.work_pos["z"])
            self.on_update_callback("work_pos:a", self.work_pos["a"])
            self.on_update_callback("work_pos:b", self.work_pos["b"])
            self.on_update_callback("work_pos", self.work_pos)

    @property
    def feed_rate(self) -> float:
        """ Getter. """
        return self.__feed_rate

    @feed_rate.setter
    def feed_rate(self, feed_rate: float) -> None:
        """ Setter. """
        if self.__feed_rate != feed_rate:
            self.on_update_callback("feed_rate", feed_rate)
        self.__feed_rate = feed_rate

    @property
    def feed_rate_max(self) -> Dict[str, float]:
        """ Getter. """
        return self.__feed_rate_max

    @feed_rate_max.setter
    def feed_rate_max(self, feedrate: Dict[str, float]) -> None:
        """ Setter. """
        data_changed = False
        pos_x = feedrate.get("x")
        pos_y = feedrate.get("y")
        pos_z = feedrate.get("z")
        pos_a = feedrate.get("a")
        pos_b = feedrate.get("b")
        if pos_x is not None:
            if self.feed_rate_max["x"] != pos_x:
                data_changed = True
                self.feed_rate_max["x"] = pos_x
        if pos_y is not None:
            if self.feed_rate_max["y"] != pos_y:
                data_changed = True
                self.feed_rate_max["y"] = pos_y
        if pos_z is not None:
            if self.feed_rate_max["z"] != pos_z:
                data_changed = True
                self.feed_rate_max["z"] = pos_z
        if pos_a is not None:
            if self.feed_rate_max["a"] != pos_a:
                data_changed = True
                self.feed_rate_max["a"] = pos_a
        if pos_b is not None:
            if self.feed_rate_max["b"] != pos_b:
                data_changed = True
                self.feed_rate_max["b"] = pos_b

        if data_changed:
            self.on_update_callback("feed_rate_max:x", self.feed_rate_max["x"])
            self.on_update_callback("feed_rate_max:y", self.feed_rate_max["y"])
            self.on_update_callback("feed_rate_max:z", self.feed_rate_max["z"])
            self.on_update_callback("feed_rate_max:a", self.feed_rate_max["a"])
            self.on_update_callback("feed_rate_max:b", self.feed_rate_max["b"])
            self.on_update_callback("feed_rate_max", self.feed_rate_max)

    @property
    def feed_rate_accel(self) -> Dict[str, float]:
        """ Getter. """
        return self.__feed_rate_accel

    @feed_rate_accel.setter
    def feed_rate_accel(self, feedrate: Dict[str, float]) -> None:
        """ Setter. """
        data_changed = False
        pos_x = feedrate.get("x")
        pos_y = feedrate.get("y")
        pos_z = feedrate.get("z")
        pos_a = feedrate.get("a")
        pos_b = feedrate.get("b")
        if pos_x is not None and self.feed_rate_accel["x"] != pos_x:
            data_changed = True
            self.feed_rate_accel["x"] = pos_x
        if pos_y is not None and self.feed_rate_accel["y"] != pos_y:
            data_changed = True
            self.feed_rate_accel["y"] = pos_y
        if pos_z is not None and self.feed_rate_accel["z"] != pos_z:
            data_changed = True
            self.feed_rate_accel["z"] = pos_z
        if pos_a is not None and self.feed_rate_accel["a"] != pos_a:
            data_changed = True
            self.feed_rate_accel["a"] = pos_a
        if pos_b is not None and self.feed_rate_accel["b"] != pos_b:
            data_changed = True
            self.feed_rate_accel["b"] = pos_b

        if data_changed:
            self.on_update_callback("feed_rate_accel:x", self.feed_rate_accel["x"])
            self.on_update_callback("feed_rate_accel:y", self.feed_rate_accel["y"])
            self.on_update_callback("feed_rate_accel:z", self.feed_rate_accel["z"])
            self.on_update_callback("feed_rate_accel:a", self.feed_rate_accel["a"])
            self.on_update_callback("feed_rate_accel:b", self.feed_rate_accel["b"])
            self.on_update_callback("feed_rate_accel", self.feed_rate_accel)

    @property
    def feed_override(self) -> float:
        """ Getter. """
        return self.__feed_override

    @feed_override.setter
    def feed_override(self, feed_override: int) -> None:
        """ Setter. """
        if self.__feed_override != feed_override:
            self.__feed_override = feed_override
            self.on_update_callback("feed_override", self.feed_override)

    @property
    def rapid_override(self) -> float:
        """ Getter. """
        return self.__rapid_override

    @rapid_override.setter
    def rapid_override(self, rapid_override: int) -> None:
        """ Setter. """
        if self.__rapid_override != rapid_override:
            self.__rapid_override = rapid_override
            self.on_update_callback("rapid_override", self.rapid_override)

    @property
    def spindle_rate(self) -> float:
        """ Getter. """
        return self.__spindle_rate

    @spindle_rate.setter
    def spindle_rate(self, spindle_rate: int) -> None:
        """ Setter. """
        if self.__spindle_rate != spindle_rate:
            self.__spindle_rate = spindle_rate
            self.on_update_callback("spindle_rate", self.spindle_rate)

    @property
    def spindle_override(self) -> float:
        """ Getter. """
        return self.__spindle_override

    @spindle_override.setter
    def spindle_override(self, spindle_override: int) -> None:
        """ Setter. """
        if self.__spindle_override != spindle_override:
            self.__spindle_override = spindle_override
            self.on_update_callback("spindle_override", self.spindle_override)

    @property
    def limit_x(self) -> float:
        """ Getter. """
        return self.__limit_x

    @limit_x.setter
    def limit_x(self, limit_x: float) -> None:
        """ Setter. """
        if self.__limit_x != limit_x:
            self.__limit_x = limit_x
            self.on_update_callback("limit_x", self.limit_x)

    @property
    def limit_y(self) -> float:
        """ Getter. """
        return self.__limit_y

    @limit_y.setter
    def limit_y(self, limit_y: float) -> None:
        """ Setter. """
        if self.__limit_y != limit_y:
            self.__limit_y = limit_y
            self.on_update_callback("limit_y", self.limit_y)

    @property
    def limit_z(self) -> float:
        """ Getter. """
        return self.__limit_z

    @limit_z.setter
    def limit_z(self, limit_z: float) -> None:
        """ Setter. """
        if self.__limit_z != limit_z:
            self.__limit_z = limit_z
            self.on_update_callback("limit_z", self.limit_z)

    @property
    def limit_a(self) -> float:
        """ Getter. """
        return self.__limit_a

    @limit_a.setter
    def limit_a(self, limit_a: float) -> None:
        """ Setter. """
        if self.__limit_a != limit_a:
            self.__limit_a = limit_a
            self.on_update_callback("limit_a", self.limit_a)

    @property
    def limit_b(self) -> float:
        """ Getter. """
        return self.__limit_b

    @limit_b.setter
    def limit_b(self, limit_b: float) -> None:
        """ Setter. """
        if self.__limit_b != limit_b:
            self.__limit_b = limit_b
            self.on_update_callback("limit_b", self.limit_b)

    @property
    def probe(self) -> bool:
        """ Getter. """
        return self.__probe

    @probe.setter
    def probe(self, probe: bool) -> None:
        """ Setter. """
        if self.__probe != probe:
            self.__probe = probe
            self.on_update_callback("probe", self.probe)

    @property
    def pause(self) -> bool:
        """ Getter. """
        return self.__pause

    @pause.setter
    def pause(self, pause: bool, reason: Optional[str] = None) -> None:
        """ Setter. """
        if self.__pause != pause:
            self.__pause = pause
            self.on_update_callback("pause", self.pause)
            if not pause:
                self.pause_reason.clear()
                self.on_update_callback("pause_reason", self.pause_reason)

    @property
    def pause_park(self) -> bool:
        """ Getter. """
        return self.__pause_park

    @pause_park.setter
    def pause_park(self, pause_park: bool) -> None:
        """ Setter. """
        if self.__pause_park != pause_park:
            self.__pause_park = pause_park
            self.on_update_callback("pause_park", self.pause_park)

    @property
    def parking(self) -> bool:
        """ Getter. """
        return self.__parking

    @parking.setter
    def parking(self, parking: bool) -> None:
        """ Setter. """
        if self.__parking != parking:
            self.__parking = parking
            self.on_update_callback("parking", self.parking)

    @property
    def halt(self) -> bool:
        """ Getter. """
        return self.__halt

    @halt.setter
    def halt(self, halt: bool) -> None:
        """ Setter. """
        if self.__halt != halt:
            self.__halt = halt
            self.on_update_callback("halt", self.halt)
            if not halt:
                self.halt_reason.clear()
                self.on_update_callback("halt_reason", self.halt_reason)

    @property
    def door(self) -> bool:
        """ Getter. """
        return self.__door

    @door.setter
    def door(self, door: bool) -> None:
        """ Setter. """
        if self.__door != door:
            self.__door = door
            self.on_update_callback("door", self.door)


class StateMachineGrbl(StateMachineBase):
    """ State Machine reflecting the state of a Grbl hardware controller. """

    GRBL_STATUS_HEADERS = {b"MPos": "machine_pos",
                           b"WPos": "work_pos",
                           b"FS": "feed_rate",    # Variable spindle.
                           b"F": "feed_rate",     # Non variable spindle.
                           b"Pn": "inputPins",
                           b"WCO": "workCoordOffset",
                           b"Ov": "overrideValues",
                           b"Bf": "bufferState",
                           b"Ln": "lineNumber",
                           b"A": "accessoryState"
                           }

    MACHINE_STATES = [
        b"Idle", b"Run", b"Hold", b"Jog", b"Alarm", b"Door", b"Check", b"Home", b"Sleep"]
    
    def __init__(self, on_update_callback: Callable[[str, Any], None]) -> None:
        super().__init__(on_update_callback)

        self.machine_state = b"Unknown"

    def __str__(self) -> str:
        output = super().__str__()

        new_output = ("Grbl state: {self.machine_state}\n")
        return output + new_output.format(self=self)

    def parse_incoming(self, incoming: bytes) -> None:
        """ Parse incoming string from Grbl controller. """
        if incoming.startswith(b"error:"):
            self._parse_incoming_error(incoming)
        elif incoming.startswith(b"ok"):
            assert False, "'ok' response should not have been passed to state machine."
        elif incoming.startswith(b"ALARM:"):
            self._parse_incoming_alarm(incoming)
        elif incoming.startswith(b"<"):
            self._parse_incoming_status(incoming)
        elif incoming.startswith(b"["):
            self._parse_incoming_feedback(incoming)
        elif incoming.startswith(b"$"):
            self._parse_setting(incoming)
        elif incoming.startswith(b">"):
            self._parse_startup(incoming)
        elif incoming.startswith(b"Grbl "):
            self._parse_welcome(incoming)
        else:
            print("Input not parsed: %s" % incoming.decode('utf-8'))

    def _parse_incoming_error(self, incoming: bytes) -> None:
        print(b"ERROR:", incoming, b"TODO")

    def _parse_incoming_status(self, incoming: bytes) -> None:
        """ "parse_incoming" determined a "status" message was received from the
        Grbl controller. Parse the status message here. """
        assert incoming.startswith(b"<") and incoming.endswith(b">")

        incoming = incoming.strip(b"<>")

        fields = incoming.split(b"|")

        machine_state = fields[0]
        self._set_state(machine_state)

        for field in fields[1:]:
            identifier, value = field.split(b":")
            assert identifier in self.GRBL_STATUS_HEADERS
            if identifier in [b"MPos", b"WPos", b"WCO"]:
                self._set_coordinates(identifier, value)
            elif identifier == b"Ov":
                self._set_overrides(value)
            elif identifier == b"FS":
                feed, spindle = value.split(b",")
                self.feed_rate = int(float(feed))
                self.spindle_rate = int(float(spindle))
            elif identifier == b"F":
                self.feed_rate = int(float(value))
            else:
                print("TODO. Unparsed status field: ", identifier, value)

        self.changes_made = True

    def _parse_incoming_feedback_modal(self, msg: bytes) -> None:
        """ Parse report on which modal option was last used for each group.
        Report comes fro one of 2 places:
        1. In response to a "$G" command, GRBL sends a G-code Parser State Message
           in the format:
           [GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0.0 S0]
        2. A Gcode line in the form "G0 X123 Y345 F2000" would update the "Motion"
           group (G0) and the Feed group (F2000).
        self.MODAL_COMMANDS maps these words to a group. eg: G0 is in the "motion" group.  """
        modals = msg.split(b" ")
        update_units = False
        for modal in modals:
            units: Dict[str, Any] = self.MODAL_GROUPS["units"]
            if modal.decode() in units:
                modal_group = self.MODAL_COMMANDS[modal]
                if modal_group in self.gcode_modal and \
                        self.gcode_modal[modal_group] != modal:
                    # Grbl has changed from mm to inches or vice versa.
                    update_units = True

            if modal in self.MODAL_COMMANDS:
                modal_group = self.MODAL_COMMANDS[modal]
                self.gcode_modal[modal_group] = modal
            elif chr(modal[0]).encode('utf-8') in self.MODAL_COMMANDS:
                modal_group = self.MODAL_COMMANDS[chr(modal[0]).encode('utf-8')]
                self.gcode_modal[modal_group] = modal
            else:
                assert False, "Gcode word does not match any mmodal group: %s" % \
                              modal.decode('utf-8')
        self.on_update_callback("gcode_modal", self.gcode_modal)

        assert not update_units, \
               "TODO: Units have changed. Lots of things will need recalculated."

    def _parse_incoming_feedback(self, incoming: bytes) -> None:
        """ "parse_incoming" determined a "feedback" message was received from the
        Grbl controller. Parse the message here and store parsed data. """
        assert incoming.startswith(b"[") and incoming.endswith(b"]")

        incoming = incoming.strip(b"[]")

        msg_type, msg = incoming.split(b":")

        if msg_type == b"MSG":
            print(msg_type, incoming, "TODO")
        elif msg_type in [b"GC", b"sentGcode"]:
            self._parse_incoming_feedback_modal(msg)
        elif msg_type == b"HLP":
            # Response to a "$" (print help) command. Only ever used by humans.
            pass
        elif msg_type in [b"G54", b"G55", b"G56", b"G57", b"G58", b"G59", b"G28",
                          b"G30", b"G92", b"TLO", b"PRB"]:
            # Response to a "$#" command.
            print(msg_type, incoming, "TODO")
        elif msg_type == b"VER":
            if len(self.version) < 1:
                self.version.append("")
            self.version[0] = incoming.decode('utf-8')
        elif msg_type == b"OPT":
            while len(self.version) < 2:
                self.version.append("")
            self.version[1] = incoming.decode('utf-8')
        elif msg_type == b"echo":
            # May be enabled when building GRBL as a debugging option.
            pass
        else:
            assert False, "Unexpected feedback packet type: %s" % msg_type.decode('utf-8')


    def _parse_incoming_alarm(self, incoming: bytes) -> None:
        """ "parse_incoming" determined a "alarm" message was received from the
        Grbl controller. Parse the alarm here. """
        print("ALARM:", incoming)

    def _parse_setting(self, incoming: bytes) -> None:
        """ "parse_incoming" determined one of the EPROM registers is being displayed.
        Parse and save the value here. """
        incoming = incoming.lstrip(b"$")
        setting, value = incoming.split(b"=")

        if setting == b"0":
            # Step pulse, microseconds
            pass
        elif setting == b"1":
            # Step idle delay, milliseconds
            pass
        elif setting == b"2":
            # Step port invert, mask
            pass
        elif setting == b"3":
            # Direction port invert, mask
            pass
        elif setting == b"4":
            # Step enable invert, boolean
            pass
        elif setting == b"5":
            # Limit pins invert, boolean
            pass
        elif setting == b"6":
            # Probe pin invert, boolean
            pass
        elif setting == b"10":
            # Status report, mask
            pass
        elif setting == b"11":
            # Junction deviation, mm
            pass
        elif setting == b"12":
            # Arc tolerance, mm
            pass
        elif setting == b"13":
            # Report inches, boolean
            pass
        elif setting == b"20":
            # Soft limits, boolean
            pass
        elif setting == b"21":
            # Hard limits, boolean
            pass
        elif setting == b"22":
            # Homing cycle, boolean
            pass
        elif setting == b"23":
            # Homing dir invert, mask
            pass
        elif setting == b"24":
            # Homing feed, mm/min
            pass
        elif setting == b"25":
            # Homing seek, mm/min
            pass
        elif setting == b"26":
            # Homing debounce, milliseconds
            pass
        elif setting == b"27":
            # Homing pull-off, mm
            pass
        elif setting == b"30":
            # Max spindle speed, RPM
            pass
        elif setting == b"31":
            # Min spindle speed, RPM
            pass
        elif setting == b"32":
            # Laser mode, boolean
            pass
        elif setting == b"100":
            # X steps/mm
            pass
        elif setting == b"101":
            # Y steps/mm
            pass
        elif setting == b"102":
            # Z steps/mm
            pass
        elif setting == b"110":
            # X Max rate, mm/min
            value_int = int(float(value))
            self.feed_rate_max = {"x": value_int}
        elif setting == b"111":
            # Y Max rate, mm/min
            value_int = int(float(value))
            self.feed_rate_max = {"y": value_int}
        elif setting == b"112":
            # Z Max rate, mm/min
            value_int = int(float(value))
            self.feed_rate_max = {"z": value_int}
        elif setting == b"120":
            # X Acceleration, mm/sec^2
            value_int = int(float(value))
            self.feed_rate_accel = {"x": value_int}
        elif setting == b"121":
            # Y Acceleration, mm/sec^2
            value_int = int(float(value))
            self.feed_rate_accel = {"y": value_int}
        elif setting == b"122":
            # Z Acceleration, mm/sec^2
            value_int = int(float(value))
            self.feed_rate_accel = {"z": value_int}
        elif setting == b"130":
            # X Max travel, mm
            pass
        elif setting == b"131":
            # Y Max travel, mm
            pass
        elif setting == b"132":
            # Z Max travel, mm
            pass
        else:
            assert False, "Unexpected setting: %s %s" % (
                setting.decode('utf-8'), value.decode('utf-8'))

    @staticmethod
    def _parse_startup(incoming: bytes) -> None:
        """ "parse_incoming" determined Grbl's startup blocks are being received.
        These are strings of Gcode that get executed on every restart. """
        print("Grbl executed the following gcode on startup: %s" %
              incoming.lstrip(">").rstrip(":ok"))
        assert incoming.startswith(b">") and incoming.endswith(b":ok")

    @staticmethod
    def _parse_welcome(incoming: bytes) -> None:
        """ "parse_incoming" determined Grbl's welcome message is being received.
        Perform any tasks appropriate to a Grbl restart here. """
        print("Startup:", incoming)
        print("Startup successful. TODO: Clear Alarm states.")

    def _set_overrides(self, value: bytes) -> None:
        """ A message from Grbl reporting one of the overrides is being applied
        has been received. Parse message and apply data here. """
        feed_override, rapid_override, spindle_override = value.split(b",")
        feed_override_int = int(float(feed_override))
        rapid_override_int = int(float(rapid_override))
        spindle_override_int = int(float(spindle_override))

        if 10 <= feed_override_int <= 200:
            self.feed_override = feed_override_int
        if rapid_override_int in [100, 50, 20]:
            self.rapid_override = rapid_override_int
        if 10 <= spindle_override_int <= 200:
            self.spindle_override = spindle_override_int

    def _set_coordinates(self, identifier: bytes, value: bytes) -> None:
        """ Set machine position according to message received from Grbl controller. """
        if identifier == b"MPos":
            self.machine_pos = self._parse_coordinates(value)
        elif identifier == b"WPos":
            self.work_pos = self._parse_coordinates(value)
        elif identifier == b"WCO":
            self.work_offset = self._parse_coordinates(value)
        else:
            print("Invalid format: %s  Expected one of [MPos, WPos, WCO]" %
                  identifier.decode('utf-8'))

    @staticmethod
    def _parse_coordinates(string: bytes) -> Dict[str, float]:
        """ Parse bytes for coordinate information. """
        parts = string.split(b",")
        if len(parts) < 3:
            print(string, parts)
        assert len(parts) >= 3, \
               "Malformed coordinates: %s" % string.decode('utf-8')
        assert len(parts) <= 4, \
               "TODO: Handle more than 4 coordinates. %s" % string.decode('utf-8')
        coordinates = {}
        coordinates["x"] = float(parts[0])
        coordinates["y"] = float(parts[1])
        coordinates["z"] = float(parts[2])
        if len(parts) > 3:
            coordinates["a"] = float(parts[3])
        return coordinates

    def _set_state(self, state: bytes) -> None:
        """ Apply State. State has been reported by Grbl controller. """
        states = state.split(b":")
        assert len(states) <= 2, "Invalid state: %s" % state.decode('utf-8')

        state = states[0]
        assert state in self.MACHINE_STATES, "Invalid state: %s" % state.decode('utf-8')
        self.machine_state = state

        if state in (b"Idle", b"Run", b"Jog", b"Home"):
            self.pause = False
            self.pause_park = False
            self.halt = False
            self.door = False
        elif state == b"Hold":
            # self.pause_park = False
            self.halt = False
            self.door = False
            self.pause = True
        elif state == b"Alarm":
            self.pause = False
            self.pause_park = False
            self.door = False
            self.halt = True
        elif state == b"Door":
            self.pause = False
            self.pause_park = False
            self.halt = False
            self.door = True
        elif state == b"Check":
            pass
        elif state == b"Sleep":
            pass
