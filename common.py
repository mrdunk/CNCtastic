import pkgutil, os, sys

#from controllers import debug

baseDir = os.path.dirname(sys.argv[0])

def loadPlugins(directory: str):
    """ Load plugins.
    Plugins whose filename starts with "_" will be ignored.
    Each file to be exported should contain a "className" variable with the name
    of the class to be exported.
    Args:
        directory: Directory relative to main.py.
    Returns:
        A dictionary of name: module pairs. """
    plugins = {}
    fullDir = os.path.join(baseDir, directory)
    for finder, name, ispkg in pkgutil.iter_modules([fullDir]):
        if name[0] == "_":
            continue
        plugin = getattr(__import__("%s.%s" % (directory, name)), name)
        if "className" in dir(plugin):
            className = getattr(plugin, "className")
            plugins[className] = getattr(plugin, className)()
            print("Plugin: %s.py %s" % (name, className))

    return plugins
