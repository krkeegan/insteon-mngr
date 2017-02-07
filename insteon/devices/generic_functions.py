class GenericFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_responder_data3(self):
        ret = self._device.group
        if ret == 0x01:
            ret = 0x00
        return ret
