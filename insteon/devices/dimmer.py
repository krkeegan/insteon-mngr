from insteon.devices import GenericSendHandler, GenericFunctions


class DimmerSendHandler(GenericSendHandler):
    '''Provides the specific command handling for the dimmer category of
    devices'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


class DimmerFunctions(GenericFunctions):
    '''Provides the specific command handling for the dimmer category of
    devices'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The following define the human readable names
        self.data_1_name = 'On Level'
        self.data_2_name = 'Ramp Rate'
        # The following define the default responder values
        self.data_1_default = 0xFF
        self.data_2_default = 0x1F

    def list_data_1_options(self):
        ret = {}
        for value in range(0x00, 0xFF+1):
            key = '{0:.1f}'.format((value/0xFF)*100) + '%'
            ret[key] = value
        return ret

    def list_data_2_options(self):
        return {
				'9 min': 0x00, '8 min': 0x01, '7 min': 0x02, '6 min': 0x03,
				'5 min': 0x04, '4.5 min': 0x05, '4 min': 0x06, '3.5 min': 0x07,
				'3 min': 0x08, '2.5 min': 0x09, '2 min': 0x0a, '1.5 min': 0x0b,
				'1 min': 0x0C, '47 sec': 0x0d, '43 sec': 0x0e, '39 sec': 0x0f,
				'34 sec': 0x10, '32 sec': 0x11, '30 sec': 0x12, '28 sec': 0x13,
				'26 sec': 0x14, '23.5 sec': 0x15, '21.5 sec': 0x16,
                '19 sec': 0x17, '8.5 sec': 0x18, '6.5 sec': 0x19,
                '4.5 sec': 0x1a, '2 sec': 0x1b, '.5 sec': 0x1c, '.3 sec': 0x1d,
				'.2 sec': 0x1e, '.1 sec': 0x1f
        }

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
