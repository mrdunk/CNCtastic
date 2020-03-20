

class _GuiPageBase:
    """ Base class for layout of GUI tabs. """
    is_valid_plugin = False
    plugin_type = "gui_pages"

    @classmethod
    def get_classname(cls) -> str:
        """ Return class name. """
        return cls.__qualname__


