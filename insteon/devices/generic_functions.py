class GenericFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_controller_data1(self, responder):
        return 0x03

    def get_controller_data2(self, responder):
        return 0x00

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

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {
            'responder': True,
        }
        ret['data_1'] = {
            'name': 'On/Off',
            'default': 0xFF,
            'values': self.list_data_1_options()
        }
        ret['data_2'] = {
            'name': 'None',
            'default': 0x00,
            'values': self.list_data_2_options()
        }
        return ret

    def _create_groups(self, group_class):
        pass
