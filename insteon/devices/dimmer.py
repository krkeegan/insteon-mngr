from insteon.devices.generic import GenericSendHandler

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
