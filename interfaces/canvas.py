from typing import List, Tuple

import random

import numpy as np
#import PySimpleGUIQt as sg       # type: ignore
from terminals.gui import sg      # type: ignore

from interfaces._interface_base import _InterfaceBase  # type: ignore

NODE_SIZE = 3

class Structure:
    def __init__(self, graph_elem) -> None:
        self.graph_elem = graph_elem
        self.nodes = np.zeros((0, 4))
        self.display_nodes = np.zeros((0, 4))
        self.edges: List[Tuple[int, int]]= []
        self.update_edges_from: int = 0

        self.node_circle_offset = (-NODE_SIZE / 2, NODE_SIZE / 2, 0, 0)

    def calculate_nodes_center(self):
        extremities = self.calculate_nodes_extremities()
        return (-(extremities[0][0] + extremities[1][0]) / 2,
                -(extremities[0][1] + extremities[1][1]) / 2,
                -(extremities[0][2] + extremities[1][2]) / 2)

    def calculate_nodes_extremities(self):
        if not len(self.nodes):
            return (1, 1, 1)
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

    def redraw(self):
        """ Reset display_nodes so they get recalculated. """
        self.display_nodes = np.zeros((0, 4))
        self.update_edges_from = 0
        self.graph_elem.Erase()

    def transform(self, nodes, scale, rotate, center):
        """ Apply a transformation defined by a center of points, desired scale
            and desired viewing angle. """
        canvas_size = self.graph_elem.CanvasSize

        t = self.translation_matrix(*center)
        t = np.dot(t, self.scale_matrix(scale, scale, scale))
        t = np.dot(t, self.rotate_z_matrix(rotate[2]))
        t = np.dot(t, self.rotate_y_matrix(rotate[1]))
        t = np.dot(t, self.rotate_x_matrix(rotate[0]))
        t = np.dot(t, self.translation_matrix(
            canvas_size[0] / 2, canvas_size[1] / 2, 0))

        return_nodes = np.dot(nodes, t)

        return return_nodes

    def translation_matrix(self, dx=0, dy=0, dz=0):
        """ Return matrix for translation along vector (dx, dy, dz). """

        return np.array([[1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [0, 0, 1, 0],
                         [dx, dy, dz, 1]])

    def scale_matrix(self, sx=0, sy=0, sz=0):
        """ Return matrix for scaling equally along all axes. """

        return np.array([[sx, 0,  0,  0],
                         [0,  sy, 0,  0],
                         [0,  0,  sz, 0],
                         [0,  0,  0,  1]])

    def rotate_x_matrix(self, radians):
        """ Return matrix for rotating about the x-axis by 'radians' radians """

        c = np.cos(radians)
        s = np.sin(radians)
        return np.array([[1, 0, 0, 0],
            [0, c,-s, 0],
            [0, s, c, 0],
            [0, 0, 0, 1]])

    def rotate_y_matrix(self, radians):
        """ Return matrix for rotating about the y-axis by 'radians' radians """

        c = np.cos(radians)
        s = np.sin(radians)
        return np.array([[ c, 0, s, 0],
            [ 0, 1, 0, 0],
            [-s, 0, c, 0],
            [ 0, 0, 0, 1]])

    def rotate_z_matrix(self, radians):
        """ Return matrix for rotating about the z-axis by 'radians' radians """

        c = np.cos(radians)
        s = np.sin(radians)
        return np.array([[c,-s, 0, 0],
            [s, c, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]])

    def add_nodes(self, nodes) -> None:
        ones_column = np.ones((len(nodes), 1))
        ones_added = np.hstack((nodes, ones_column))
        self.nodes = np.vstack((self.nodes, ones_added))

    def addEdges(self, edgeList):
        self.edges += edgeList

    def update(self, scale, rotate, center) -> None:
        if len(self.nodes) > len(self.display_nodes):
            update_nodes_from = len(self.display_nodes)
            new_nodes = self.transform(
                    self.nodes[update_nodes_from:], scale, rotate, center)

            color = "blue"
            for node in new_nodes:
                corrected = node + self.node_circle_offset
                self.graph_elem.DrawCircle(corrected[:2], NODE_SIZE, color)
            self.display_nodes = np.vstack((self.display_nodes, new_nodes))

        if self.update_edges_from < len(self.edges):
            for edge in self.edges[self.update_edges_from:]:
                color = "blue"
                if len(edge) > 2:
                    color = edge[2]
                node_0 = self.display_nodes[edge[0]]
                node_1 = self.display_nodes[edge[1]]
                self.graph_elem.DrawLine(node_0[:2], node_1[:2], width=1, color=color)
            self.update_edges_from = len(self.edges)


class TestCube(Structure):
    def __init__(self, graph_elem) -> None:
        super().__init__(graph_elem)

        self.add_nodes([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)])
        self.addEdges([(0, 4, "red")])
        self.addEdges([(n, n + 4) for n in range(1, 4)])
        self.addEdges([(n, n + 1) for n in range(0, 8, 2)])
        self.addEdges([(n, n + 2) for n in (0, 1, 4, 5)])


class Axis(Structure):
    def __init__(self, graph_elem) -> None:
        super().__init__(graph_elem)

        self.add_nodes([(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)])
        self.addEdges([(0, 1, "red"), (0, 2, "green"), (0, 3, "blue")])


class CanvasWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    def __init__(self, label: str = "canvasWidget") -> None:
        super().__init__(label)

        self.graph_elem = sg.Graph((400, 400), (0, 0), (400, 400), key='+GRAPH+',
                                   tooltip='Graph')

        self.rotate_x = 0.6161012
        self.rotate_y = 0
        self.rotate_z = 3.141 / 4
        self.scale = 100

        self.structures = {}

        # Display a cube for debugging purposes.
        self.structures["test_cube"] = TestCube(self.graph_elem)
        self.structures["axis"] = Axis(self.graph_elem)

        self.event_subscriptions = {
            "active_controller:machine_pos": ("_machine_pos_handler", None),
            "gui:keypress": ("_keypress_handler", None),
            }

    def _machine_pos_handler(self, pos):
        print("pos: ", pos)
        self.add_nodes([(pos["x"], pos["y"], pos["z"])])

    def _keypress_handler(self, key):
        print("key: ", key)
        # TODO: Replace "special xxxx" with sensible named variable.
        if key == "special 16777234":
            self.rotate_z += 0.01
        elif key == "special 16777236":
            self.rotate_z -= 0.01
        elif key == "special 16777235":
            self.rotate_x -= 0.01
        elif key == "special 16777237":
            self.rotate_x += 0.01
        elif key == "+":
            self.scale *= 1.1
        elif key == "-":
            self.scale /= 1.1

        self.redraw()

    def gui_layout(self) -> List:
        """ Layout information for the PySimpleGUI interface. """

        frame = [
            [self.graph_elem, sg.Stretch()],
        ]

        layout = [
            [sg.Text('Plot test', size=(50, 2), key="foobar")],
            [sg.Frame('Graphing Group', frame)],
            ]

        return layout

    def calculate_center(self):
        combined_extremities = ([None, None, None], [None, None, None])
        for structure in self.structures.values():
            extremities = structure.calculate_nodes_extremities()
            # Minimum extremities.
            for index, value in enumerate(extremities[0]):
                if(combined_extremities[0][index] is None or
                   extremities[0][index] < combined_extremities[0][index]):
                    combined_extremities[0][index] = extremities[0][index]
            # Maximum extremities.
            for index, value in enumerate(extremities[1]):
                if(combined_extremities[1][index] is None or
                   extremities[1][index] < combined_extremities[1][index]):
                    combined_extremities[1][index] = extremities[1][index]

        return (-(combined_extremities[0][0] + combined_extremities[1][0]) / 2,
                -(combined_extremities[0][1] + combined_extremities[1][1]) / 2,
                -(combined_extremities[0][2] + combined_extremities[1][2]) / 2)

    def redraw(self) -> None:
        for structure in self.structures.values():
            structure.redraw()

    def update(self) -> None:
        super().update()

        rotate = (self.rotate_x, self.rotate_y, self.rotate_z)

        for structure in self.structures.values():
            structure.update(self.scale, rotate, self.calculate_center())
