from insteon_mngr.devices import GenericSendHandler, GenericFunctions
from insteon_mngr.base_objects import Group


class DimmerFunctions(GenericFunctions):
    '''Provides the specific functions unique to dimmer devices'''
    def __init__(self, device):
        super().__init__(device, group_class=DimmerGroup)

class DimmerSendHandler(GenericSendHandler):
    '''Provides the specific command handling for the dimmer category of
    devices'''
    #################################################################
    #
    # Message Schema
    #
    #################################################################

    @property
    def msg_schema(self):
        schema = super().msg_schema
        schema['on'] = {
            'cmd_1': {'default': 0x11},
            'cmd_2': {'default': 0xFF,
                      'name': 'on_level'},
            'msg_length': 'standard',
            'message_type': 'direct'
        }
        return schema


class DimmerGroup(Group):

    def __init__(self, device, **kwargs):
        super().__init__(device, **kwargs)
        self._type = 'dimmer'

    def list_data_1_options(self):
        ret = {}
        for value in range(0x00, 0xFF+1):
            key = '{0:0>6.1%}'.format(value/0xFF)
            ret[key] = value
        return ret

    def list_data_2_options(self):
        return {
				'540 sec': 0x00, '480 sec': 0x01, '420 sec': 0x02,
                '360 sec': 0x03, '300 sec': 0x04, '270 sec': 0x05,
                '240 sec': 0x06, '210 sec': 0x07, '180 sec': 0x08,
                '150 sec': 0x09, '120 sec': 0x0a, '150 sec': 0x0b,
				'120 sec': 0x0C, '047 sec': 0x0d, '043 sec': 0x0e,
                '039 sec': 0x0f, '034 sec': 0x10, '032 sec': 0x11,
                '030 sec': 0x12, '028 sec': 0x13, '026 sec': 0x14,
                '023.5 sec': 0x15, '021.5 sec': 0x16, '019 sec': 0x17,
                '008.5 sec': 0x18, '006.5 sec': 0x19, '004.5 sec': 0x1a,
                '002 sec': 0x1b, '000.5 sec': 0x1c, '000.3 sec': 0x1d,
                '000.2 sec': 0x1e, '000.1 sec': 0x1f
        }

    def _state_commands(self):
        ret = super()._state_commands()
        dimmer = {}
        for i in range(0, 256):
            msg = self.device.create_message('on')
            msg.insert_bytes_into_raw({'on_level': i})
            dimmer[str(i)] = msg
        ret.update(dimmer)
        return ret

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = super().get_features()
        ret['data_1'] = {
            'name': 'On Level',
            'default': 0xFF,
            'values': self.list_data_1_options()
        }
        ret['data_2'] = {
            'name': 'Ramp Rate',
            'default': 0x1F,
            'values': self.list_data_2_options()
        }
        return ret
