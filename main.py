#!/usr/bin/env python3
""" Control computerised machine tools using G-Code programming language.
https://en.wikipedia.org/wiki/G-code

Uses plugins for different hardware controller types. (Eg, Grbl, etc.)
Uses plugins for different operating modes. (Eg. Jog, run GCode file, etc.)
"""

import argparse

import common
from coordinator.coordinator import Coordinator


def main() -> None:
    """ Main program loop. """

    terminals = common.loadPlugins("terminals")
    controllers = common.loadPlugins("controllers")
    interfaces = common.loadPlugins("interfaces")

    parser = argparse.ArgumentParser(description="A UI for CNC machines.")

    parser.add_argument("-debug_show_events",
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
        terminal.active: bool = getattr(args, terminal.label)   # type: ignore
        terminal.debug_show_events: bool = args.debug_show_events   # type: ignore


    coordinator = Coordinator(terminals, interfaces, controllers, args.debug_show_events)


    while True:
        if not coordinator.updateComponents():
            break

    coordinator.close()
    print("done")

if __name__ == "__main__":
    main()
