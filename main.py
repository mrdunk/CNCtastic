#!/usr/bin/env python3

import argparse

import common
from definitions import ConnectionState
from coordinator.coordinator import Coordinator


def main():

    terminals = common.loadPlugins("terminals")
    controllers = common.loadPlugins("controllers")
    interfaces = common.loadPlugins("interfaces")

    parser = argparse.ArgumentParser(description="A UI for CNC machines.")

    parser.add_argument("-debugShowEvents",
                        action="store_true",
                        help="Display events.")

    for terminal in terminals:
        if terminal.activeByDefault:
            parser.add_argument("-no_%s" % terminal.label,
                                dest=terminal.label,
                                action="store_false",
                                help=terminal.description)
        else:
            parser.add_argument("-%s" % terminal.label,
                                dest=terminal.label,
                                action="store_true",
                                help=terminal.description)
    
    args = parser.parse_args()
    print(args)

    for terminal in terminals:
        terminal.activateNow = getattr(args, terminal.label)
        terminal.debugShowEvents = args.debugShowEvents

    
    coordinator = Coordinator(terminals, interfaces, controllers)


    while True:
        if not coordinator.updateComponents():
            break

    coordinator.close()
    print("done")

if __name__ == "__main__":
    main()
