""" Parse and process gcode supplied in text format by event. """

from typing import Any, List

from collections import namedtuple
import numpy as np
from pygcode import Line, GCodeMotion
from pygcode.exceptions import GCodeWordStrError

from core_components._core_component_base import _CoreComponentBase

Section = namedtuple("Section", ["name", "lines", "errors"])
ParsedLine = namedtuple("ParsedLine", ["raw", "gcode_word_key", "count", "iterations"])
GcodeIteration = namedtuple("GcodeIteration", ["gcode", "errors", "metadata"])
GcodeMetadata = namedtuple("GcodeMetadata", ["point", "distance"])


class CoreGcode(_CoreComponentBase):
    """ Parse and process gcode supplied in text format by event. """
    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    label = "__core_gcode__"

    def __init__(self) -> None:
        super().__init__(self.label)

        self.gcode_raw: List[str] = []
        self.gcode_raw_error: bool = False

        self.gcode_parsed: List[Section] = []

        self.event_subscriptions["core_gcode:gcode_raw_loaded"] = (
            "_on_gcode_raw", "")

    def _on_gcode_raw(self, _: str, gcode_raw: Any) -> None:

        self.gcode_raw = gcode_raw
        self.gcode_parsed = []

        section_name = "unnamed"
        section: List[ParsedLine] = []
        section_errors: List[str] = []
        last_point = np.array([np.nan, np.nan, np.nan])
        count = 0
        for line in gcode_raw:
            section_name_parsed, parsed_line = \
                    self._gcode_parse_line(section_name, last_point, count, line)
            if section_name_parsed != section_name:
                # New section.
                if section:
                    # Save old section.
                    self.gcode_parsed.append(Section(section_name, section, section_errors))
                    section = []
                    section_errors = []
                section_name = section_name_parsed
            else:
                if parsed_line.iterations[0].gcode:
                    # Valid gcode line containing more than just comment.
                    last_point = parsed_line.iterations[0].metadata.point

                section.append(parsed_line)
                count += 1
                if parsed_line.iterations[0].errors:
                    for error_ in parsed_line.iterations[0].errors:
                        section_errors.append("%s: %s" % (error_, line))

        if section:
            # Save remainder of section.
            self.gcode_parsed.append(Section(section_name, section, section_errors))

        self.publish("core_gcode:parsed_gcode_loaded", self.gcode_parsed)

    def _gcode_parse_line(self,
                          section_name: str,
                          last_point: np.array,
                          count: int,
                          line: str) -> ParsedLine:
        errors = []
        point = np.array([np.nan, np.nan, np.nan])
        gcode_word_key = None
        distance = None
        gcode_line = None
        try:
            gcode_line = Line(line)
        except GCodeWordStrError:
            errors.append("Invalid gcode")

        if gcode_line:
            point, point_errors, gcode_word_key = self._gcode_to_point(gcode_line, last_point)
            errors += point_errors

            distance = self._dist_between_points(last_point, point)
            if np.isnan(distance):
                distance = None

            if isinstance(gcode_line, Line) and not gcode_line.block and gcode_line.comment:
                # Only a comment in this line. No other gcode.
                comment = str(gcode_line.comment)
                if comment.upper().replace(" ", "").startswith("(SECTION:"):
                    section_name = comment.split(":", 1)[1].rstrip(")").strip()
                    print(">>", section_name)
        metadata = GcodeMetadata(point, distance)
        gcode_iteration = GcodeIteration(gcode_line, errors, metadata)
        return (section_name, ParsedLine(line, gcode_word_key, count, [gcode_iteration]))

    def _gcode_append_comment(self, line: Line, comment: str) -> None:
        """ Add new comment or append to existing comment. """
        line.comment = "%s ; %s" % (line.comment, comment)

    def _dist_between_points(self, point_1: np.array, point_2: np.array) -> Any:
        return np.linalg.norm(point_1 - point_2)

    def _gcode_to_point(self, line: Line, last: np.array) -> np.array:

        return_value = last.copy()
        gcode_word_key = None
        errors = []
        found_motion = False
        for gcode in line.block.gcodes:
            if isinstance(gcode, GCodeMotion):
                if found_motion:
                    errors.append("Multiple GCodeMotion on one line")
                found_motion = True

                params = gcode.get_param_dict()
                if "X" in params:
                    return_value[0] = params["X"]
                if "Y" in params:
                    return_value[1] = params["Y"]
                if "Z" in params:
                    return_value[2] = params["Z"]
                gcode_word_key = gcode.word_key

        return (return_value, errors, gcode_word_key)
