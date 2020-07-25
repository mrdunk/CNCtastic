# pylint: disable=E1101  # Module 'PySimpleGUIQt' has no 'XXXX' member (no-member)

""" Display Gcode and machine movement in the GUI. """

from typing import List, Tuple, Dict, Union, Optional, Any, Type

import numpy as np
from PySide2.QtCore import Qt, QRectF
from PySide2.QtGui import QPainter
from PySimpleGUI_loader import sg
from pygcode import GCodeRapidMove

from controllers._controller_base import _ControllerBase
from gui_pages._page_base import _GuiPageBase

NODE_SIZE = 3

class Geometry:
    """ A collection of nodes and edges that make up some geometry in 3d space. """

    def __init__(self, graph_elem: sg.Graph) -> None:
        self.graph_elem = graph_elem
        self.nodes = np.zeros((0, 4))
        self.display_nodes = np.zeros((0, 4))
        self.edges: List[Tuple[int, int, Optional[str]]] = []
        self.update_edges_from: int = 0
        self.calculate_center_include = True

        self.node_circle_offset = (-NODE_SIZE / 2, NODE_SIZE / 2, 0, 0)

    def calculate_nodes_center(self) -> Tuple[float, float, float]:
        """ Return the center of all the nodes. """
        extremities = self.calculate_bounding_box()
        return (-(extremities[0][0] + extremities[1][0]) / 2,
                -(extremities[0][1] + extremities[1][1]) / 2,
                -(extremities[0][2] + extremities[1][2]) / 2)

    def calculate_bounding_box(self) -> \
            Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """ Return the maximum and minimum values for each axis. """
        if not self.nodes.any():
            return ((0, 0, 0), (1, 1, 1))
        max_x = self.nodes[0][0]
        min_x = self.nodes[0][0]
        max_y = self.nodes[0][1]
        min_y = self.nodes[0][1]
        max_z = self.nodes[0][2]
        min_z = self.nodes[0][2]
        for node in self.nodes:
            if node[0] > max_x:
                max_x = node[0]
            if node[0] < min_x:
                min_x = node[0]
            if node[1] > max_y:
                max_y = node[1]
            if node[1] < min_y:
                min_y = node[1]
            if node[2] > max_z:
                max_z = node[2]
            if node[2] < min_z:
                min_z = node[2]

        return ((min_x, min_y, min_z), (max_x, max_y, max_z))

    def redraw(self) -> None:
        """ Reset display_nodes so they get recalculated. """
        self.display_nodes = np.zeros((0, 4))
        self.update_edges_from = 0
        self.graph_elem.Erase()

    def transform(self,
                  nodes: np.array,
                  scale: float,
                  rotate: Tuple[float, float, float],
                  center: Tuple[float, float, float]
                  ) -> np.array:
        """ Apply a transformation defined by a center of points, desired scale
            and desired viewing angle. """
        canvas_size = self.graph_elem.CanvasSize

        modifier = self.translation_matrix(*center)
        modifier = np.dot(modifier, self.scale_matrix(scale, scale, scale))
        modifier = np.dot(modifier, self.rotate_z_matrix(rotate[2]))
        modifier = np.dot(modifier, self.rotate_y_matrix(rotate[1]))
        modifier = np.dot(modifier, self.rotate_x_matrix(rotate[0]))
        modifier = np.dot(modifier, self.translation_matrix(
            canvas_size[0] / 2, canvas_size[1] / 2, 0))

        return_nodes = np.dot(nodes, modifier)

        return return_nodes

    @classmethod
    def translation_matrix(cls,
                           dif_x: float = 0,
                           dif_y: float = 0,
                           dif_z: float = 0) -> np.array:
        """ Return matrix for translation along vector (dif_x, dif_y, dif_z). """

        return np.array([[1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [0, 0, 1, 0],
                         [dif_x, dif_y, dif_z, 1]])

    @classmethod
    def scale_matrix(cls,
                     scale_x: float = 0,
                     scale_y: float = 0,
                     scale_z: float = 0) -> np.array:
        """ Return matrix for scaling equally along all axes. """

        return np.array([[scale_x, 0, 0, 0],
                         [0, scale_y, 0, 0],
                         [0, 0, scale_z, 0],
                         [0, 0, 0, 1]])

    @classmethod
    def rotate_x_matrix(cls, radians: float) -> np.array:
        """ Return matrix for rotating about the x-axis by 'radians' radians """

        cos = np.cos(radians)
        sin = np.sin(radians)
        return np.array([[1, 0, 0, 0],
                         [0, cos, -sin, 0],
                         [0, sin, cos, 0],
                         [0, 0, 0, 1]])

    @classmethod
    def rotate_y_matrix(cls, radians: float) -> np.array:
        """ Return matrix for rotating about the y-axis by 'radians' radians """

        cos = np.cos(radians)
        sin = np.sin(radians)
        return np.array([[cos, 0, sin, 0],
                         [0, 1, 0, 0],
                         [-sin, 0, cos, 0],
                         [0, 0, 0, 1]])

    @classmethod
    def rotate_z_matrix(cls, radians: float) -> np.array:
        """ Return matrix for rotating about the z-axis by 'radians' radians """

        cos = np.cos(radians)
        sin = np.sin(radians)
        return np.array([[cos, -sin, 0, 0],
                         [sin, cos, 0, 0],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])

    def add_nodes(self, nodes: np.array) -> None:
        """ Add points to geometry. """
        ones_column = np.ones((len(nodes), 1))
        ones_added = np.hstack((nodes, ones_column))
        self.nodes = np.vstack((self.nodes, ones_added))

    def add_edges(self, edge_list: List[Tuple[int, int, Optional[str]]]) -> None:
        """ Add edges between 2 nodes. """
        self.edges += edge_list

    def update(self,
               scale: float,
               rotate: Tuple[float, float, float],
               center: Tuple[float, float, float]
               ) -> bool:
        """ Draw/redraw any nodes and edges that have been added since last update.
        Returns: Boolean value indicating if anything was done. """
        work_done = False
        color: Optional[str]
        if len(self.nodes) > len(self.display_nodes):
            work_done = True
            update_nodes_from = len(self.display_nodes)
            new_nodes = self.transform(
                self.nodes[update_nodes_from:], scale, rotate, center)

            color = "blue"
            for node in new_nodes:
                corrected = node + self.node_circle_offset
                self.graph_elem.DrawCircle(tuple(corrected[:2]), NODE_SIZE, color)
            self.display_nodes = np.vstack((self.display_nodes, new_nodes))

        if self.update_edges_from < len(self.edges):
            work_done = True
            for edge in self.edges[self.update_edges_from:]:
                color = "blue"
                if len(edge) > 2:
                    color = edge[2]
                node_0 = self.display_nodes[edge[0]]
                node_1 = self.display_nodes[edge[1]]
                self.graph_elem.DrawLine(tuple(node_0[:2]),
                                         tuple(node_1[:2]),
                                         width=10,
                                         color=color)
            self.update_edges_from = len(self.edges)
        return work_done

class TestCube(Geometry):
    """ A Geometry object with some sample data added. """

    def __init__(self, graph_elem: sg.Graph) -> None:
        super().__init__(graph_elem)

        self.add_nodes([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)])
        self.add_edges([(0, 4, "red")])
        self.add_edges([(n, n + 4, None) for n in range(1, 4)])
        self.add_edges([(n, n + 1, None) for n in range(0, 8, 2)])
        self.add_edges([(n, n + 2, None) for n in (0, 1, 4, 5)])


class Axis(Geometry):
    """ Geometry object displaying X, Y & Z axis. """

    def __init__(self, graph_elem: sg.Graph) -> None:
        super().__init__(graph_elem)

        self.add_nodes([(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)])
        self.add_edges([(0, 1, "red"), (0, 2, "green"), (0, 3, "blue")])

        self.calculate_center_include = False


class CanvasWidget(_GuiPageBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    label = "canvasWidget"

    def __init__(self,
                 controllers: Dict[str, _ControllerBase],
                 controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        super().__init__(controllers, controller_classes)

        width = 800
        height = 800
        self.graph_elem = sg.Graph((width, height),
                                   (0, 0),
                                   (width, height),
                                   key="+GRAPH+",
                                   tooltip="Graph",
                                   background_color="white",
                                   enable_events=True,
                                   drag_submits=True)

        self.rotation: Dict[str, float] = {"x": 0.6161012, "y": 0, "z": 3.141 / 4}
        self.scale: float = 50
        self.mouse_move: Optional[Tuple[float, float]] = None

        # Display a cube for debugging purposes.
        self.structures: Dict[str, Geometry] = {}
        self.structures["test_cube"] = TestCube(self.graph_elem)
        self.structures["axis"] = Axis(self.graph_elem)
        self.structures["machine_position"] = Geometry(self.graph_elem)
        self.structures["gcode"] = Geometry(self.graph_elem)

        self.center: Tuple[float, float, float] = self.calculate_center()

        self.event_subscriptions = {
            "active_controller:machine_pos": ("_machine_pos_handler", None),
            "gui:keypress": ("_keypress_handler", None),
            "gui:restart": ("redraw", None),
            "gui:has_restarted": ("_startup", None),
            "core_gcode:parsed_gcode_loaded": ("_gcode_handler", None),
            }

        self.dirty: bool = True

    def _startup(self, _: Any) -> None:
        try:
            self.graph_elem.QT_QGraphicsView.mouse_moveEvent = self.mouse_move_event
            self.graph_elem.QT_QGraphicsView.mousePressEvent = self.mouse_press_event
            self.graph_elem.QT_QGraphicsView.mouseReleaseEvent = self.mouse_release_event
            self.graph_elem.QT_QGraphicsView.resizeEvent = self.resize_event
            self.graph_elem.QT_QGraphicsView.wheelEvent = self.wheel_event

            self.graph_elem.QT_QGraphicsView.DragMode = \
                    self.graph_elem.QT_QGraphicsView.ScrollHandDrag
            self.graph_elem.QT_QGraphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.graph_elem.QT_QGraphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.graph_elem.QT_QGraphicsView.setRenderHints(
                    QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
            #self.graph_elem.QT_QGraphicsView.setAlignment(Qt.AlignCenter)
        except AttributeError:
            pass

        self.dirty = True

    def _machine_pos_handler(self, pos: Dict[str, float]) -> None:
        """ Event handler for "active_controller:machine_pos".
            Called when the machine position is updated."""
        machine_position = self.structures["machine_position"]
        machine_position.add_nodes([(pos["x"], pos["y"], pos["z"])])

    def _gcode_handler(self, gcode: str) -> None:
        """ Draw gcode primitives. """
        # TODO
        print("canvas._gcode_handler")
        nodes = []
        edges = []
        for section in gcode:
            print("section:", section.name)
            for line in section.lines:
                if line.iterations[0].errors:
                    continue
                if not line.gcode_word_key:
                    continue
                point = line.iterations[0].metadata.point
                if np.isnan(np.sum(point)):
                    continue
                nodes.append(point)

                color = "green"
                if line.gcode_word_key == GCodeRapidMove().word_key:
                    color = "red"
                if len(nodes) > 1:
                    edges.append((len(nodes) - 2, len(nodes) - 1, color))
        self.structures["gcode"].add_nodes(nodes)
        self.structures["gcode"].add_edges(edges)

        self.dirty = True

    def _keypress_handler(self, key: Union[int, slice]) -> None:
        # TODO: Replace "special xxxx" with sensible named variable.
        if key == "special 16777234":
            self.rotation["z"] += 0.01
        elif key == "special 16777236":
            self.rotation["z"] -= 0.01
        elif key == "special 16777235":
            self.rotation["x"] -= 0.01
        elif key == "special 16777237":
            self.rotation["x"] += 0.01
        elif key == "+":
            self.scale *= 1.1
        elif key == "-":
            self.scale /= 1.1

        self.redraw()

    def gui_layout(self) -> List[List[sg.Element]]:
        """ Layout information for the PySimpleGUI interface. """
        frame = [
            [self.graph_elem, sg.Stretch()],
        ]

        layout = [
            [sg.Text('Plot test', size=(50, 2), key="foobar")],
            [sg.Frame('Graphing Group', frame)],
            ]

        return layout

    def calculate_bounding_box(self) -> Tuple[Tuple[float, float, float],
                                              Tuple[float, float, float]]:
        """ Calculate minimum and maximum coordinate values encompassing all points. """
        # Would have preferred to use None here but mypy doesn't like Optional[float].
        max_value: float = 9999999999
        combined_minimums: List[float] = [max_value, max_value, max_value]
        combined_maximums: List[float] = [-max_value, -max_value, -max_value]

        for structure in self.structures.values():
            if not structure.calculate_center_include:
                continue

            extremities = structure.calculate_bounding_box()

            mimimums = extremities[0]
            for index, value in enumerate(mimimums):
                assert -max_value < value < max_value, "Coordinate out of range."
                if value < combined_minimums[index]:
                    combined_minimums[index] = value

            maximums = extremities[1]
            for index, value in enumerate(maximums):
                assert -max_value < value < max_value, "Coordinate out of range."
                if value > combined_maximums[index]:
                    combined_maximums[index] = value

        for value in combined_minimums:
            if value == max_value:
                return (0, 0, 0)
        for value in combined_maximums:
            if value == -max_value:
                return (0, 0, 0)

        return (combined_minimums, combined_maximums)

    def calculate_center(self) -> Tuple[float, float, float]:
        """ Calculate the center of all geometry. """

        combined_minimums, combined_maximums = self.calculate_bounding_box()

        return (-(combined_minimums[0] + combined_maximums[0]) / 2,
                -(combined_minimums[1] + combined_maximums[1]) / 2,
                -(combined_minimums[2] + combined_maximums[2]) / 2)

    def redraw(self, *_: Any) -> None:
        """ Redraw all geometry to screen. """
        for structure in self.structures.values():
            structure.redraw()
        self.dirty = False

    def mouse_move_event(self, event: Any) -> None:
        """ Called on mouse button move inside canvas element. """
        if self.mouse_move:
            move = (event.x() - self.mouse_move[0], event.y() - self.mouse_move[1])
            self.mouse_move = (event.x(), event.y())

        self.center = (
                self.center[0] + move[0] / 10,
                self.center[1] + move[1] / 10,
                self.center[2])
        self.dirty = True

    def mouse_press_event(self, event: Any) -> None:
        """ Called on mouse button down inside canvas element. """
        print("There are", len(self.graph_elem.QT_QGraphicsView.items(event.pos())),
              "items at position", self.graph_elem.QT_QGraphicsView.mapToScene(event.pos()))
        self.graph_elem.QT_QGraphicsView.setDragMode(
            self.graph_elem.QT_QGraphicsView.ScrollHandDrag)

        self.mouse_move = (event.x(), event.y())

    def mouse_release_event(self, event: Any) -> None:
        """ Called on mouse button release inside canvas element. """
        self.graph_elem.QT_QGraphicsView.setDragMode(self.graph_elem.QT_QGraphicsView.NoDrag)

        self.mouse_move = None

    def resize_event(self, event: Any) -> None:
        """ Called on window resize. """
        print(event)
        #self.dirty = True

    def wheel_event(self, event: Any) -> None:
        """ Called on mousewheel inside canvas element. """
        if event.delta() > 0:
            scale = 1.1
        else:
            scale = 0.9
        self.graph_elem.QT_QGraphicsView.scale(scale, scale)

        #self.scale += float(event.delta()) / 16
        #if self.scale < 1:
        #    self.scale = 1
        #else:
        #    self.dirty = True

    def set_viewport(self) -> None:
        for structure in self.structures.values():
            if len(structure.nodes) != len(structure.display_nodes):
                # This structure is not finished being drawn to the scene.
                # We don't want to re-size until everything is displayed or
                # we might flicker between scales as things are drawing.
                return
        self.center = self.calculate_center()
        try:
            # If we are using QT...
            screenRect = self.graph_elem.QT_QGraphicsView.scene().itemsBoundingRect()
            self.graph_elem.QT_QGraphicsView.setSceneRect(screenRect)
        except AttributeError:
            pass

    def update(self) -> None:
        """ Update all Geometry objects. """
        super().update()

        if self.dirty:
            self.redraw()

        rotate = (self.rotation["x"], self.rotation["y"], self.rotation["z"])

        work_done = False
        for structure in self.structures.values():
            work_done |= structure.update(self.scale, rotate, self.center)
        if work_done:
            self.set_viewport()
