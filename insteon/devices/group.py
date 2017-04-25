from insteon.plm_message import PLM_Message
from insteon.sequences import (WriteALDBRecordModem, WriteALDBRecordi2,
    WriteALDBRecordi1)


class GroupSendHandler(object):
    '''Provides the basic command handling for group object.  Devices, whose
    group has distinct commands and needs should create their own send handler
    class that inherits and overrides the necessary elements'''
    def __init__(self, group):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._group = group

    def delete_record(self, key=None):
        if self._group.device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self)
        else:
            link_sequence = WriteALDBRecordi1(self)
        link_sequence.key = key
        link_sequence.in_use = False
        return link_sequence

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


class PLMGroupSendHandler(GroupSendHandler):
    '''Provides the basic command handling for plm group object.'''
    def __init__(self, group):
        super().__init__(group)

    def _state_commands(self):
        on_plm_bytes = {
            'group': self._group.group_number,
            'cmd_1': 0x11,
            'cmd_2': 0x00,
        }
        on_message = PLM_Message(self._group.device.plm,
                                 plm_cmd='all_link_send',
                                 plm_bytes=on_plm_bytes)
        off_plm_bytes = {
            'group': self._group.group_number,
            'cmd_1': 0x13,
            'cmd_2': 0x00,
        }
        off_message = PLM_Message(self._group.device.plm,
                                  plm_cmd='all_link_send',
                                  plm_bytes=off_plm_bytes)
        ret = {
            'ON': on_message,
            'OFF': off_message
        }
        return ret

    def delete_record(self, key=None):
        link_sequence = WriteALDBRecordModem(group=self._group)
        link_sequence.key = key
        link_sequence.in_use = False
        return link_sequence

    def state(self, state):
        commands = self._state_commands()
        try:
            message = commands[state.upper()]
        except KeyError:
            print('This device doesn\'t know the state', state)
        else:
            message.state_machine = 'all_link_send'
            records = self._group.device.plm.aldb.get_matching_records({
                'controller': True,
                'group': self._group.group_number,
                'in_use': True
            })
            # Until all link status is complete, sending any other cmds to PLM
            # will cause it to abandon all link process
            message.seq_lock = True
            # Time with retries for failed objects, plus we actively end it on
            # success
            wait_time = (len(records) + 1) * (87 / 1000 * 18)
            message.seq_time = wait_time
            message.extra_ack_time = wait_time
            self._group.device.plm.queue_device_msg(message)

class PLMGroupFunctions(GroupFunctions):
    def __init__(self, group):
        super().__init__(group)

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = super().get_features()
        ret['responder'] = False
        return ret
