from insteon.plm_message import PLM_Message
from insteon.sequences import (WriteALDBRecordModem, WriteALDBRecordi2,
    WriteALDBRecordi1)


class GroupSendHandler(object):
    '''Provides the basic command handling for group object.  Devices, whose
    group has distinct commands and needs should create their own send handler
    class that inherits and overrides the necessary elements'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device

    def create_controller_link_sequence(self, user_link):
        '''Creates a controller link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        if self._device.root.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self._device)
        else:
            link_sequence = WriteALDBRecordi1(self._device)
        if user_link.controller_key is not None:
            link_sequence.key = user_link.controller_key
        link_sequence.controller = True
        link_sequence.linked_device = user_link.device
        link_sequence.data1 = self._device.root.functions.get_controller_data1(None)
        link_sequence.data2 = self._device.root.functions.get_controller_data2(None)
        return link_sequence

    def create_responder_link_sequence(self, user_link):
        '''Creates a responder link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        if self._device.root.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self._device)
        else:
            link_sequence = WriteALDBRecordi1(self._device)
        if user_link.responder_key is not None:
            link_sequence.key = user_link.responder_key
        link_sequence.controller = False
        link_sequence.linked_device = user_link.controller_device
        link_sequence.data1 = user_link.data_1
        link_sequence.data2 = user_link.data_2
        return link_sequence

class GroupFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {
            'responder': False
        }
        return ret


class PLMGroupSendHandler(GroupSendHandler):
    '''Provides the basic command handling for plm group object.'''
    def __init__(self, device):
        super().__init__(device)

    def _state_commands(self):
        on_plm_bytes = {
            'group': self._device.group_number,
            'cmd_1': 0x11,
            'cmd_2': 0x00,
        }
        on_message = PLM_Message(self._device.root.plm,
                                 plm_cmd='all_link_send',
                                 plm_bytes=on_plm_bytes)
        off_plm_bytes = {
            'group': self._device.group_number,
            'cmd_1': 0x13,
            'cmd_2': 0x00,
        }
        off_message = PLM_Message(self._device.root.plm,
                                  plm_cmd='all_link_send',
                                  plm_bytes=off_plm_bytes)
        ret = {
            'ON': on_message,
            'OFF': off_message
        }
        return ret

    def create_controller_link_sequence(self, user_link):
        '''Creates a controller link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        link_sequence = WriteALDBRecordModem(self._device)
        link_sequence.controller = True
        link_sequence.linked_device = user_link.device
        return link_sequence

    def create_responder_link_sequence(self, user_link):
        # TODO Is the modem ever a responder in a way that this would be needed?
        return NotImplemented

    def state(self, state):
        commands = self._state_commands()
        try:
            message = commands[state.upper()]
        except KeyError:
            print('This device doesn\'t know the state', state)
        else:
            message.state_machine = 'all_link_send'
            records = self._device.root.plm.aldb.get_matching_records({
                'controller': True,
                'group': self._device.group_number,
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
            self._device.root.plm.queue_device_msg(message)

class PLMGroupFunctions(GroupFunctions):
    def __init__(self, device):
        super().__init__(device)

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = super().get_features()
        return ret
