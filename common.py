""" Misc library methods. """

from typing import List, Any, Set
import pkgutil
import importlib
import os
import sys

#from controllers import debug
from component import _ComponentBase

BASEDIR = os.path.dirname(sys.argv[0])

def get_component_from_module(module) -> _ComponentBase:
    """ Yields plugin classes when provided with """
    for thing_name in dir(module):
        thing = getattr(module, thing_name)

        is_valid_plugin = False
        try:
            is_valid_plugin = getattr(thing, "is_valid_plugin")
        except AttributeError:
            pass
        else:
            if is_valid_plugin:
                yield thing

def load_plugins(directory: str) -> List[Any]:
    """ Load plugins.
    Plugins whose filename starts with "_" will be ignored.
    Args:
        directory: Directory relative to main.py.
    Returns:
        A Set of plugins. """

    print("Loading %s plugins:" % directory)
    plugins: Set[Any] = set([])

    full_dir = os.path.join(BASEDIR, directory)

    discovered_plugins = [
        importlib.import_module(directory + "." + name)
        for finder, name, ispkg in pkgutil.iter_modules([full_dir])
        if not name.startswith('_')
        ]

    for module in discovered_plugins:
        for thing in get_component_from_module(module):
            if directory.startswith(thing.plugin_type):
                active_by_default: bool = True
                if "active_by_default" in dir(thing):
                    active_by_default = getattr(thing, "active_by_default")

                print("  type: %s\tname: %s\tactive_by_default: %s\t" %
                      (thing.plugin_type, thing.get_classname(), active_by_default))
                plugins.add((active_by_default, thing))

    return plugins
