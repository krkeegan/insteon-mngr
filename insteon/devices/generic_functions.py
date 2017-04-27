from insteon.base_objects import Group


class GenericFunctions(object):
    def __init__(self, device, group_class=None):
        self._device = device
        if group_class is None:
            group_class = Group
        self._group_class = group_class
        self.refresh_groups()

    def refresh_groups(self):
        self._device.create_group(self._device.base_group_number, self._group_class)

    def get_controller_data1(self, responder):
        return 0x03

    def get_controller_data2(self, responder):
        return 0x00

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {}
        return ret
