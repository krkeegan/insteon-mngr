from insteon.plm_message import PLM_Message


class GroupSendHandler(object):
    '''Provides the basic command handling for group object.  Devices, whose
    group has distinct commands and needs should create their own send handler
    class that inherits and overrides the necessary elements'''
    def __init__(self, group):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._group = group


class GroupFunctions(object):
    def __init__(self, group):
        self._group = group


class PLMGroupSendHandler(object):
    '''Provides the basic command handling for plm group object.'''
    def __init__(self, group):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._group = group

    def set_state(self, is_on=False):
        '''Send an on/off command to a plm group'''
        command = 0x11
        if not is_on:
            command = 0x13
        plm_bytes = {
            'group': self._group.group_number,
            'cmd_1': command,
            'cmd_2': 0x00,
        }
        message = PLM_Message(self._group.plm,
                              plm_cmd='all_link_send',
                              plm_bytes=plm_bytes)
        message.state_machine = 'all_link_send'
        records = self._group.plm.aldb.get_matching_records({
            'controller': True,
            'group': self._group.group_number,
            'in_use': True
        })
        # Until all link status is complete, sending any other cmds to PLM
        # will cause it to abandon all link process
        message.seq_lock = True
        # Time with retries for failed objects, plus we actively end it on
        # success
        message.seq_time = (len(records) + 1) * (87 / 1000 * 18)
        self._group.plm.queue_device_msg(message)
