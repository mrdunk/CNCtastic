#!/usr/bin/env python3
""" Control computerised machine tools using G-Code programming language.
https://en.wikipedia.org/wiki/G-code

Uses plugins for different hardware controller types. (Eg, Grbl, etc.)
Uses plugins for different operating modes. (Eg. Jog, run GCode file, etc.)
"""

from typing import List
import argparse

import common
from coordinator.coordinator import Coordinator
from terminals._terminal_base import _TerminalBase
from controllers._controller_base import _ControllerBase
from interfaces._interface_base import _InterfaceBase


def main() -> None:
    """ Main program loop. """

    # Component plugin classes.
    class_terminals = common.load_plugins("terminals")
    class_controllers = common.load_plugins("controllers")
    class_interfaces = common.load_plugins("interfaces")

    # Component plugin instances.
    terminals: List[_TerminalBase] = \
        []
    controllers: List[_ControllerBase] = \
        [controller() for active, controller in class_controllers if active]
    interfaces: List[_InterfaceBase] = \
        [interface() for active, interface in class_interfaces if active]

    # Command line arguments.
    parser = argparse.ArgumentParser(description="A UI for CNC machines.")

    parser.add_argument("-debug_show_events",
                        action="store_true",
                        help="Display events.")

    for active_by_default, terminal in class_terminals:
        if active_by_default:
            parser.add_argument("-no_%s" % terminal.get_classname(),
                                dest=terminal.get_classname(),
                                action="store_false",
                                help="terminal.description")
        else:
            parser.add_argument("-%s" % terminal.get_classname(),
                                dest=terminal.get_classname(),
                                action="store_true",
                                help="terminal.description")

    args = parser.parse_args()
    print(args)

    # Instantiate terminals according to command line flags.
    for _, terminal in class_terminals:
        if getattr(args, terminal.get_classname()):
            terminal_instance = terminal()
            terminal_instance.debug_show_events = args.debug_show_events
            terminals.append(terminal_instance)

    # Populate and start the coordinator.
    coordinator = Coordinator(terminals, interfaces, controllers, args.debug_show_events)

    while True:
        if not coordinator.update_components():
            break

    # Cleanup and exit.
    coordinator.close()
    print("done")

if __name__ == "__main__":
    main()
