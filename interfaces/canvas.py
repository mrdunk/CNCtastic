from typing import List, Tuple

import random

import numpy as np
#import PySimpleGUIQt as sg       # type: ignore
from terminals.gui import sg      # type: ignore

from interfaces._interface_base import _InterfaceBase  # type: ignore


class CanvasWidget(_InterfaceBase):
    """ Allows user to directly control various machine settings. eg: Jog the
    head to given coordinates. """

    # Set this True for any derived class that is to be used as a plugin.
    is_valid_plugin = True

    NODE_SIZE = 3

    def __init__(self, label: str = "canvasWidget") -> None:
        super().__init__(label)

        self.nodes = np.zeros((0, 4))
        self.display_nodes = np.zeros((0, 4))
        self.edges: List[Tuple[int, int]]= []
        self.update_nodes_from: int = 0
        self.update_edges_from: int = 0

        self.rotate_x = 0.6161012
        self.rotate_y = 0
        self.rotate_z = 3.141 / 4
        self.scale = 100

        # Display a cube for debugging purposes.
        self.add_nodes([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)])
        self.addEdges([(n, n + 4) for n in range(0, 4)])
        self.addEdges([(n, n + 1) for n in range(0, 8, 2)])
        self.addEdges([(n, n + 2) for n in (0, 1, 4, 5)])

        self.cutter_circle_offset = (-self.NODE_SIZE / 2, self.NODE_SIZE / 2, 0, 0)

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

    def calculate_nodes_center(self):
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

        return (-(max_x + min_x) / 2,
                -(max_y + min_y) / 2,
                -(max_z + min_z) / 2)

    def redraw(self):
        """ Reset display_nodes so they get recalculated. """
        self.display_nodes = np.zeros((0, 4))
        self.update_edges_from = 0
        self.graph_elem.Erase()

    def transform(self, nodes):
        """ Apply a transformation defined by a given matrix. """
        canvas_size = self.graph_elem.CanvasSize

        t = self.translation_matrix(*self.calculate_nodes_center())
        t = np.dot(t, self.scale_matrix(self.scale, self.scale, self.scale))
        t = np.dot(t, self.rotate_z_matrix(self.rotate_z))
        t = np.dot(t, self.rotate_y_matrix(self.rotate_y))
        t = np.dot(t, self.rotate_x_matrix(self.rotate_x))
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

    def gui_layout(self) -> List:
        """ Layout information for the PySimpleGUI interface. """

        self.graph_elem = sg.Graph((400, 400), (0, 0), (400, 400), key='+GRAPH+',
                                   tooltip='Graph')
        frame = [
            [self.graph_elem, sg.Stretch()],
        ]

        layout = [
            [sg.Text('Plot test', size=(50, 2), key="foobar")],
            [sg.Frame('Graphing Group', frame)],
            ]

        return layout

    def update(self) -> None:
        super().update()

        #self.i += 0.01
        #if round(self.i * 100) % 5 == 0:
        #    self.screen_rotate_y = self.rotate_y_matrix(self.i)
        #    self.display_nodes = np.zeros((0, 4))
        #    self.update_edges_from = 0
        #    self.graph_elem.Erase()

        if len(self.nodes) > len(self.display_nodes):
            update_nodes_from = len(self.display_nodes)
            new_nodes = self.transform(self.nodes[update_nodes_from:])

            color = "red"
            for node in new_nodes:
                corrected = node + self.cutter_circle_offset
                self.graph_elem.DrawCircle(corrected[:2], self.NODE_SIZE, color)
                color = "blue"
            self.display_nodes = np.vstack((self.display_nodes, new_nodes))

        if self.update_edges_from < len(self.edges):
            color = "red"
            for edge in self.edges[self.update_edges_from:]:
                node_0 = self.display_nodes[edge[0]]
                node_1 = self.display_nodes[edge[1]]
                self.graph_elem.DrawLine(node_0[:2], node_1[:2], width=1, color=color)
                color = "blue"
            self.update_edges_from = len(self.edges)
