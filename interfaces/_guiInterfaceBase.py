from typing import List

from interfaces._interfaceBase import _InterfaceBase


class _GuiInterfaceBase(_InterfaceBase):
    def guiLayout(self) -> List:
        """ Return widget layout information for pySimpleGUI. """
        raise NotImplementedError
        return []


