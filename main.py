import PySimpleGUI as sg

import common
from definitions import ConnectionState
from coordinator.coordinator import Coordinator

#sg.theme('DarkAmber') 

def main():

    terminals = common.loadPlugins("terminals")
    controllers = common.loadPlugins("controllers")
    interfaces = common.loadPlugins("interfaces")
    coordinator = Coordinator(terminals, interfaces, controllers)


    while True:
        if not coordinator.update():
            break

    coordinator.close()
    print("done")

if __name__ == "__main__":
    main()
