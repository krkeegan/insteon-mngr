from insteon.plm_message import PLM_Message
from insteon.sequences import (WriteALDBRecordModem, WriteALDBRecordi2,
    WriteALDBRecordi1)


class GroupFunctions(object):
    def __init__(self, group):
        self._group = group

    def state_str(self):
        '''Returns the current state of the device in a human readable form'''
        # TODO do we want to return an unknown value? trigger status if not?
        ret = 'OFF'
        if self._group.state == 0xFF:
            ret = 'ON'
        return ret

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

class PLMGroupFunctions(GroupFunctions):
    def __init__(self, group):
        super().__init__(group)

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = super().get_features()
        ret['responder'] = False
        return ret
