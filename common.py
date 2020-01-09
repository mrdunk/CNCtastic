from typing import List, Any
import pkgutil, os, sys

#from controllers import debug

baseDir = os.path.dirname(sys.argv[0])

def loadPlugins(directory: str) -> List[Any]:
    """ Load plugins.
    Plugins whose filename starts with "_" will be ignored.
    Each file to be exported should contain a "className" variable with the name
    of the class to be exported.
    Args:
        directory: Directory relative to main.py.
    Returns:
        A dictionary of name: module pairs. """
    plugins: List[Any] = []
    fullDir = os.path.join(baseDir, directory)
    for finder, name, ispkg in pkgutil.iter_modules([fullDir]):
        if name[0] == "_":
            continue
        plugin = getattr(__import__("%s.%s" % (directory, name)), name)
        if "className" in dir(plugin):
            className = getattr(plugin, "className")

            plugin = getattr(plugin, className)()
            plugins.append(plugin)
            
            print("Plugin: %s.py %s as %s" % (name, className, plugin.label))

    return plugins
