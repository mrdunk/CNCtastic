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

    NODE_SIZE = 15

    def __init__(self, label: str = "canvasWidget") -> None:
        super().__init__(label)

        self.nodes = np.zeros((0, 4))
        self.display_nodes = np.zeros((0, 4))
        self.edges: List[Tuple[int, int]]= []
        self.update_nodes_from: int = 0
        self.update_edges_from: int = 0

        self.screen_translation = self.translation_matrix(200, 100, 0)
        self.screen_scale = self.scale_matrix(100, 100, 100)
        #self.screen_rotate_x = self.rotate_x_matrix(0)
        self.screen_rotate_x = self.rotate_x_matrix(0.6161012)
        self.screen_rotate_y = self.rotate_y_matrix(0)
        #self.screen_rotate_y = self.rotate_y_matrix(0.6161012)
        self.screen_rotate_z = self.rotate_z_matrix(3.141 / 4)

        self.add_nodes([(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)])

        self.addEdges([(n, n + 4) for n in range(0, 4)])
        self.addEdges([(n, n + 1) for n in range(0, 8, 2)])
        self.addEdges([(n, n + 2) for n in (0, 1, 4, 5)])

        self.cutter_circle_offset = (-self.NODE_SIZE / 2, self.NODE_SIZE / 2, 0, 0)

        self.i = 0

    def transform(self, nodes):
        """ Apply a transformation defined by a given matrix. """
        nodes = np.dot(nodes, self.screen_scale)
        nodes = np.dot(nodes, self.screen_rotate_z)
        nodes = np.dot(nodes, self.screen_rotate_x)
        nodes = np.dot(nodes, self.screen_rotate_y)
        nodes = np.dot(nodes, self.screen_translation)
        return nodes

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
        #transformed = self.transform(ones_added)
        #self.nodes = np.vstack((self.nodes, transformed))
        self.nodes = np.vstack((self.nodes, ones_added))

    def addEdges(self, edgeList):
        self.edges += edgeList

    def gui_layout(self) -> List:
        """ Layout information for the PySimpleGUI interface. """

        self.graph_elem = sg.Graph((400, 400), (0, 0), (400, 400), key='+GRAPH+', tooltip='Graph')
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

            for node in new_nodes:
                corrected = node + self.cutter_circle_offset
                self.graph_elem.DrawCircle(corrected[:2], self.NODE_SIZE, 'blue')
            self.display_nodes = np.vstack((self.display_nodes, new_nodes))

        if self.update_edges_from < len(self.edges):
            for edge in self.edges[self.update_edges_from:]:
                node_0 = self.display_nodes[edge[0]]
                node_1 = self.display_nodes[edge[1]]
                self.graph_elem.DrawLine(node_0[:2], node_1[:2], width=1, color="blue")
            self.update_edges_from = len(self.edges)
