class GenericFunctions(object):
    def __init__(self, device):
        self._device = device
        # The following define the human readable names
        self.data_1_name = 'On/Off'
        self.data_2_name = 'None'
        # The following define the default responder values
        self.data_1_default = 0xFF
        self.data_2_default = 0x00

    def get_responder_data3(self):
        '''Returns the correct data3 value for responder links on this device'''
        ret = self._device.group
        if ret == 0x01:
            ret = 0x00
        return ret

    def state_str(self):
        '''Returns the current state of the device in a human readable form'''
        # TODO do we want to return an unknown value? trigger status if not?
        ret = 'OFF'
        if self._device.state == 0xFF:
            ret = 'ON'
        return ret

    def initialize_device(self, group_class=None):
        '''Called when the device is first loaded or created.  Calls any
        initialization functions which are unique to this device.'''
        self._create_groups(group_class)

    def list_data_1_options(self):
        return {'ON': 0xFF,
                'OFF': 0x00}

    def list_data_2_options(self):
        return {'None': 0x00}

    def get_link_details(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {}
        ret['data_1'] = {
            'name': self.data_1_name,
            'default': self.data_1_default,
            'values': self.list_data_1_options()
        }
        ret['data_2'] = {
            'name': self.data_2_name,
            'default': self.data_2_default,
            'values': self.list_data_2_options()
        }
        return ret

    def _create_groups(self, group_class):
        # All devices have a group 0x01, other specialized devices may have more
        if self._device.get_object_by_group_num(0x01) is None:
            self._device.create_group(0x01, group_class)
