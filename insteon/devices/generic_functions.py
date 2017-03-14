class GenericFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_responder_data3(self):
        ret = self._device.group
        if ret == 0x01:
            ret = 0x00
        return ret

    def state_str(self):
        # TODO do we want to return an unknown value? trigger status if not?
        ret = 'OFF'
        if self._device.state == 0xFF:
            ret = 'ON'
        return ret

    def initialize_device(self, group_class=None):
        '''Called when the device is first loaded or created.  Calls any
        initialization functions which are unique to this device.'''
        self._create_groups(group_class)

    def _create_groups(self, group_class):
        # All devices have a group 0x01, other specialized devices may have more
        if self._device.get_object_by_group_num(0x01) is None:
            self._device.create_group(0x01, group_class)
