from typing import List, Dict

from coordinator.coordinator import _CoreComponent


def diffDicts(original: Dict, new: Dict) -> Dict:
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
    diff = {}
    for key in new:

        # Values got from the GUI tend to be converted to strings.
        # Safest to presume they are floats.
        try:
            new[key] = float(new[key])
        except ValueError:
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


class _TerminalBase(_CoreComponent):
    def __init__(self, layouts: List=[], label="gui"):
        super().__init__(label)

    def service(self) -> bool:
        """ To be called once per frame.
        Returns:
            bool: True: Continue execution.
                  False: An "Exit" or empty event occurred. Stop execution. """
        raise NotImplementedError

