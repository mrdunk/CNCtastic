""" Terminals are the plugins used for providing input and receiving output.
    This contains code common to all terminals. """

from typing import Dict, Any, Type

from component import _ComponentBase
from interfaces._interface_base import _InterfaceBase
from controllers._controller_base import _ControllerBase


def diff_dicts(original: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """ Compare 2 Dicts, returning any values that differ.
    It is presumed that the new Dict will contain all keys that are in the
    original Dict. The new Dict may have some keys that were not in the original.
    We also convert any numerical string values to floats as this is the most
    likely use.
    Args:
        original: A Dict to compare "new" against.
        new: A Dict of the expected values.
    Returns:
        A Dict of key:value pairs from "new" where either the key did not exist
            in "original" or the value differs. """
    if not isinstance(original, Dict) or not isinstance(new, Dict):
        print("ERROR: %s or %s not Dict" % (original, new))
        return {}

    diff = {}
    for key in new:
        # Values got from the GUI tend to be converted to strings.
        # Safest to presume they are floats.
        try:
            new[key] = float(new[key])
        except ValueError:
            pass
        except TypeError:
            pass

        value = new[key]
        if key in original:
            if value != original[key]:
                diff[key] = value
        else:
            # New key:value.
            # key did not exist in original.
            diff[key] = value

    return diff


class _TerminalBase(_ComponentBase):

    active_by_default = True

    plugin_type = "terminal"

    def __init__(self, label: str = "_guiBase") -> None:
        super().__init__(label)
        self.active = False

        self.interfaces: Dict[str, _InterfaceBase] = {}
        self.controllers: Dict[str, _ControllerBase] = {}
        self.controller_classes: Dict[str, Type[_ControllerBase]] = {}
        self.sub_components: Dict[str, Any] = {}

    def setup(self,
              interfaces: Dict[str, _InterfaceBase],
              controllers: Dict[str, _ControllerBase],
              controller_classes: Dict[str, Type[_ControllerBase]]) -> None:
        """ Any configuration to be done after __init__ once other components
        are active. """
        self.interfaces = interfaces
        self.controllers = controllers
        self.controller_classes = controller_classes

    def early_update(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        raise NotImplementedError
        return True  # pylint: disable=W0101 #  Unreachable code (unreachable)

    def close(self) -> None:
        """ Perform any cleanup here. """
