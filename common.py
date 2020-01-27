""" Misc library methods. """

from typing import List, Any
import pkgutil
import os
import sys

#from controllers import debug

BASEDIR = os.path.dirname(sys.argv[0])

def load_plugins(directory: str) -> List[Any]:
    """ Load plugins.
    Plugins whose filename starts with "_" will be ignored.
    Each file to be exported should contain a "class_name" variable with the name
    of the class to be exported.
    Args:
        directory: Directory relative to main.py.
    Returns:
        A dictionary of name: module pairs. """
    plugins: List[Any] = []
    full_dir = os.path.join(BASEDIR, directory)
    for _, name, _ in pkgutil.iter_modules([full_dir]):
        if name[0] == "_":
            continue
        plugin = getattr(__import__("%s.%s" % (directory, name)), name)
        # TODO: Can we do away with the class_name requirement?
        if "class_name" in dir(plugin):
            class_name = getattr(plugin, "class_name")

            plugin = getattr(plugin, class_name)()
            plugins.append(plugin)

            print("Plugin: %s.py %s as %s" % (name, class_name, plugin.label))

    return plugins
