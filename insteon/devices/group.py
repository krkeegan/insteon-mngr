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

    def get_link_details(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {}
        return ret


class PLMGroupSendHandler(object):
    '''Provides the basic command handling for plm group object.'''
    def __init__(self, group):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._group = group

    def _state_commands(self):
        on_plm_bytes = {
            'group': self._group.group_number,
            'cmd_1': 0x11,
            'cmd_2': 0x00,
        }
        on_message = PLM_Message(self._group.root.plm,
                                 plm_cmd='all_link_send',
                                 plm_bytes=on_plm_bytes)
        off_plm_bytes = {
            'group': self._group.group_number,
            'cmd_1': 0x13,
            'cmd_2': 0x00,
        }
        off_message = PLM_Message(self._group.root.plm,
                                  plm_cmd='all_link_send',
                                  plm_bytes=off_plm_bytes)
        ret = {
            'ON': on_message,
            'OFF': off_message
        }
        return ret

    def state(self, state):
        commands = self._state_commands()
        try:
            message = commands[state.upper()]
        except KeyError:
            print('This device doesn\'t know the state', state)
        else:
            message.state_machine = 'all_link_send'
            records = self._group.root.plm.aldb.get_matching_records({
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
            self._group.root.plm.queue_device_msg(message)
