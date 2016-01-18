from .base import BaseCommands


class SwitchCommands(BaseCommands):

    def __init__(self, device):
        self._device = device
