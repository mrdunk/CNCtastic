import PySimpleGUI as sg

import common
from definitions import ConnectionState
from coordinator.coordinator import Coordinator
from gui import Gui

sg.theme('DarkAmber') 

def main():


    controllers = common.loadPlugins("controllers").values()
    interfaces = common.loadPlugins("interfaces").values()
    coordinator = Coordinator(interfaces, controllers)

    gui = Gui(coordinator)

    while True:
        coordinator.controllers["debug"].readyForPull = True
        coordinator.controllers["debug"].readyForPush = True
        coordinator.update()

        if not gui.service():
            break


if __name__ == "__main__":
    main()
