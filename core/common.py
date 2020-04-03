""" Misc library methods. """

from typing import Any, Set, Iterator
import pkgutil
import importlib
import os
import sys
import inspect

#from controllers import debug
from core.component import _ComponentBase

BASEDIR = os.path.dirname(sys.argv[0])

def get_component_from_module(module: Any) -> Iterator[_ComponentBase]:
    """ Yields plugin classes when provided with """
    for _, object_ in inspect.getmembers(module):
        is_valid_plugin = False
        try:
            is_valid_plugin = getattr(object_, "is_valid_plugin")
        except AttributeError:
            pass
        else:
            if is_valid_plugin:
                yield object_

def load_plugins(directory: str) -> Set[Any]:
    """ Load plugins.
    Plugins whose filename starts with "_" will be ignored.
    Args:
        directory: Directory relative to main.py.
    Returns:
        A Set of plugins. """

    print("Loading %s plugins:" % directory)
    plugins: Set[Any] = set([])

    full_dir = os.path.join(BASEDIR, directory)
    full_mod_path = full_dir.replace("/", ".").strip(".")

    # for finder, name, ispkg in pkgutil.iter_modules([full_dir]):
    #    print(finder, name, ispkg, full_mod_path + "." + name)

    discovered_plugins = [
        importlib.import_module(full_mod_path + "." + name)
        for finder, name, ispkg in pkgutil.iter_modules([full_mod_path])
        if name and not name.startswith('_')
        ]

    for module in discovered_plugins:
        for thing in get_component_from_module(module):
            if(isinstance(thing.plugin_type, str) and
               directory.startswith(thing.plugin_type)):
                active_by_default: bool = True
                if "active_by_default" in dir(thing):
                    active_by_default = getattr(thing, "active_by_default")

                if (active_by_default, thing) not in plugins:
                    print("  type: %s\tname: %s\tactive_by_default: %s\t" %
                          (thing.plugin_type, thing.get_classname(), active_by_default))
                    plugins.add((active_by_default, thing))

    return plugins
