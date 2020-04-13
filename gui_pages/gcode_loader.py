""" A GUI page plugin for selecting and configuring controllers. """

from typing import List, Dict, Type, Any

from collections import namedtuple

from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase
from gui_pages._page_base import _GuiPageBase

# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)
from PySimpleGUIQt_loader import sg

Section = namedtuple("Section", ["name", "lines", "errors"])
ParsedLine = namedtuple("ParsedLine", ["raw", "gcode_word_key", "count", "iterations"])
GcodeIteration = namedtuple("GcodeIteration", ["gcode", "errors", "metadata"])
GcodeMetadata = namedtuple("GcodeMetadata", ["point", "distance"])


# Icons from here:
# http://www.iconarchive.com/show/small-n-flat-icons-by-paomedia.html
ERROR = b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACaklEQVR42mNkoBAwYhMMkBLRcRUXCpDn4lAH8R9++3Fz78v3G9Y9e30FrwE6fNyC043UZ6jwcIViMfz/3S/fV2edv5Fx6ePX9xgGaAM1r7fUPczLyqKNz8lf/vy9Gnz8ki3MELgBh+yNVqrycoWBOUIiDAzv3qDqRBIDumSVzYGz4XAD/CRFdGYaa1wC8/kEGFh6ZzP827KG4d/GlWANTP7hDEw+IQx/ilMZGD59AHsn+9xNPVCYgA2YZKBWEyoj1gxi//n3j+GTrSuDWEYhw791SyEGBEUzvJrRz8B3eDcDCxMTWGz901e1WedvtYAN2GClu9hciD8G5tqff/4yfHPyZBBNzQPzX8+exMC1bzsDOwsz3Edn339a4nP0UizYgI2WuivMhPnDkb38z92fgS0mFcz+tWQ2A9POjShBcvbdp5U+xy5FgA1YYKwxy11SJBUmyeQdzMAUkcjwetZEMF80LZ/h34r5DP+2roUbsOfFm9mxZ26kgQ0oUJJKK9NUnMnIyMjwj5efgblzOsPbpXMZuA/uAiv+au/GIBydzPC3PJOB6fNHhv///zP03niQ3nv36SywAarcHEJbrPQe8LGz8f4DSr5mZGYQ+PMb7mdQmHxgYWUQ/f+XgQloyaefvz77H7+scOPL93fwdFCrKlOQrCzbjxxQ2ADIsAX3nhQ23Ho8ASMpT9FRnOAqKZrPy8bKAPIOSjoGuuzzr98Me1+8mZh1+V4B1rwAAkmyYiHRMqKNYpwcWqzMkDj//fcfw+vvP68te/Kqfs7jV2uQ1WPNjSBgKcCjLsnBpg5S8Oznr5vH33+5iU0dAKnA6BGuCO59AAAAAElFTkSuQmCC"
OK = b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACKklEQVR42mNkoBAwYhMUcFfX4bVRDGCTEVAH8X89/Xjz85H7Gz7suHEFrwEcaqKCcm1eMzgUhEKxGP7/58P3qx9Vb8v4fuPVewwDQJqVZ4UeZuZh18bn5L9ff129l77aFmYI3AC11XErORSFw4jxN9Alq24GLwiHG8DvqqYj3+59CVeYgIAnnyHDwS/XGL79+wn2zqOa7XqgMAFrkG10rxH01mrGpTleyAGMr3x/xJD/dB7Df6DY+x03ah/XbG8BG6A8J2wxt4F0DIjNxcQO1gS1Ca75z7+/DI23lzIcYbrLwMjIyPD18vMldxNXxEIMmBu2gltfOpwbqLlTKhZow3+G8mdLGEIFLOGaG24uYTjKCNTMwgSx4MrzlXcSVkSADVDo85/FZ6eUKvKfm6FfJpFBmlOE4dWfjwxiLPxQzYuBmu/BNYPAp6P3Zz/I35AGNkAs1TxNPM1yJogt/JWdYaJ6GtgQkOZ6oOZjaJr////P8GrOyfSXM4/PAhvAriQkpDI/8gEzNxsvSBJkSK9qMsOsR9sxNEPTwue7ySsVftx58w4ebZKFdgXCoQb9TGzMYBsYP/1i+M/NiqH536+/DG/XXix83ntwAkZSBibjCbzWivlMXKzgkEZJx0BD/337zfD5+IOJjyq2FmDNCyAgEmkYIhSo28gixKXFyAqx/f/vfwx/3n+79m7Dlfo3S8+tQVaPM+VxG8uos0rwgnPj75efb3498+QmNnUAwlnmEQu8fYwAAAAASUVORK5CYII="
MEH = b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABkElEQVR42mNkoBAw4pKwl2HVytD418ivIPl/0flv/SvOvjtOkgEdlmy13tK/moQ0FBiOP/0/NWT+wxySDNg2o+UkHyuDmYq2GsM/RpYHUuZBikQboKdvIN4/ZfozIJNJR0uDgZmZiSE1KVF3/bp1V4gyIC0jMzE8Om4eiA0zYPWK5ZWZGRkdRBmw0YNxvRLP/wAQGxQGjExMDO+//zum3f3AmqABsjwM7Ns8GN4AmTzIBgDB36AFzyRPPPrxGq8BEZYq7sUOcjtgfGlNZQYmiAEMU3fciG9ecnARXgM6+yZONDE1y4PxYWEAAtevXVtpa2UZgdeAHfsO3WVlZVXCZsD///8/GOnriT5+9OgPVgMcVQW1ukIMryKLIXsBBCrnHXCcv+/mAQwDfA1ZtSIVmAp1mX+mIBuAFIgQb7z/tXrS0ZcNG8/9vgY3INme3aI/hmvHz49/+f/++IfiJTZeLqAqhEMZmf4xMLP/+Viy7JvHrP0/T4BlenxECtXF2CwYSAB33vw+UbjpdT8jKZqwAQArU4UReCz9MAAAAABJRU5ErkJggg=="

class GcodeLoader(_GuiPageBase):
    """ A GUI page plugin for selecting and configuring controllers. """
    is_valid_plugin = True

    label = "GcodeLoader"

    def __init__(self,
                 interfaces: Dict[str, _InterfaceBase],
                 controllers: Dict[str, _ControllerBase],
                 controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        super().__init__(interfaces, controllers, controller_classes)

        self.filename_candidate: str = ""
        self.gcode_parsed: List[Section] = []
        self.widgets: Dict[str, Any] = {}

        self.event_subscriptions["_TREE_"] = ("_on_tree", None)
        self.event_subscriptions[self.key_gen("selected_gcode_file")] = ("_on_file_picked", "")
        self.event_subscriptions["core_gcode:parsed_gcode_loaded"] = ("_on_parsed_gcode", None)
        self.event_subscriptions["gui:select_file_gcode"] = ("_on_select_file_gcode", None)

    def _file_picker(self) -> sg.Frame:
        """ Create a widget for selecting a gcode file from disk. """
        # TODO: Make last used directory sticky.
        if "file_picker_frame" in self.widgets:
            return self.widgets["file_picker_frame"]

        self.widgets["file_picker"] = sg.Input(
            size=(30, 1), key=self.key_gen("selected_gcode_file"), visible=False)
        self.widgets["file_browse"] = sg.FileBrowse(
            size=(5, 1), file_types=(("gcode", "*.ng*"), ("All files", "*.*"),))
        self.widgets["feedback"] = sg.Text(key=self.key_gen("feedback"))

        self.widgets["file_picker_frame"] = sg.Frame(
            "File picker",
            [
                [sg.Text("Filename")],
                [self.widgets["file_picker"], self.widgets["file_browse"]],
                [self.widgets["feedback"]],
                ],
            size=(30, 30),
            #visible=visible,
            )
        return self.widgets["file_picker_frame"]

    def _tree(self) -> sg.Tree:
        """ Create a tree widget for displaying loaded gcode. """
        if "tree" in self.widgets:
            return self.widgets["tree"]

        treedata = sg.TreeData()
        self.widgets["tree"] = sg.Tree(data=treedata,
                                       headings=["distance", "status", "count"],
                                       #visible_column_map=[False, True, False],
                                       change_submits=True,
                                       enable_events=True,
                                       auto_size_columns=True,
                                       num_rows=20,
                                       col0_width=50,
                                       def_col_width=50,
                                       key='_TREE_',
                                       #show_expanded=True,
                                       size=(800, 300),
                                       #debug_key=True,
                                       )

        return self.widgets["tree"]

    def gui_layout(self) -> List[List[List[sg.Element]]]:
        """ Return the GUI page for uploading Gcode. """

        output = [
            [self._file_picker()],
            [self._tree()],
            ]
        return output

    def _on_tree(self, event: str, value: str) -> None:
        """ Called whenever the selected line on the tree widget changes. """
        #print("_on_tree", event, value)

    def _on_file_picked(self, _: str, event_value: Any) -> None:
        """ Called in response to gcode file being selected. """
        if not event_value:
            return

        self.filename_candidate = event_value
        lines = []
        try:
            with open(self.filename_candidate) as file_:
                while True:
                    line = file_.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
        except IOError as error:
            self.widgets["feedback"].Update(value="Error: %s" % str(error))

        if lines:
            self.widgets["feedback"].Update(value="Loaded: %s" % self.filename_candidate)
            self.publish("core_gcode:gcode_raw_loaded", lines)
        else:
            self.widgets["feedback"].Update(value="File empty: %s" % self.filename_candidate)

    def _on_parsed_gcode(self, _: str, gcode: List[Section]) -> None:
        """ Called in response to gcode being parsed, sanitised, etc. """
        self.gcode_parsed = gcode

        treedata = sg.TreeData()
        for section in gcode:
            assert len(section) == 3
            section_name = section.name
            section_key = self.key_gen("section__%s" % section_name)

            if section.errors:
                # Errors present.
                treedata.Insert("", section_key, section_name, [], MEH)
            else:
                treedata.Insert("", section_key, section_name, [], OK)

            counter = 0
            for parsed_line in section.lines:
                block_key = self.key_gen("block__%s__%s" % (section_name, counter))

                data = ""
                if parsed_line.iterations[0].gcode:
                    data = str(parsed_line.iterations[0].gcode)
                else:
                    data = parsed_line.raw

                icon = OK
                if parsed_line.iterations[0].errors:
                    icon = ERROR
                    data += " : %s" % str(parsed_line.iterations[0].errors)

                distance = str(parsed_line.iterations[0].metadata.distance)
                if distance == "None":
                    distance = ""
                treedata.Insert(section_key,
                                block_key,
                                data,
                                [distance, icon, parsed_line.count],
                                )
                counter += 1

        self.widgets["tree"].Update(treedata)

    def _on_select_file_gcode(self, _: str, __: Any) -> None:
        """ Called in response to select_file_gcode event. """
        self.publish("gui:set_tab", "GcodeLoader")
        self.widgets["file_browse"].Click()
