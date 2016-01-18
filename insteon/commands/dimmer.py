from .base import BaseCommands

class DimmerCommands(BaseCommands):

    def __init__(self, device):
        self._device = device
