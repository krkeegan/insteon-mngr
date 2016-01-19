from insteon.plm_message import PLM_Message
from insteon.base_objects import Base_Insteon


class Insteon_Group(Base_Insteon):

    def __init__(self, parent, group_number, **kwargs):
        self._parent = parent
        super().__init__(self._parent.core, self._parent.plm, **kwargs)
        self._group_number = group_number

    @property
    def group_number(self):
        return self._group_number

    @property
    def parent(self):
        return self._parent

    def create_link(self, responder, d1, d2, d3):
        pass
        self.parent._aldb.create_controller(responder)
        responder._aldb.create_responder(self, d1, d2, d3)

    def set_dev_addr(*args, **kwargs):
        return NotImplemented

    def set_dev_version(*args, **kwargs):
        return NotImplemented

class PLM_Group(Insteon_Group):

    def __init__(self, parent, group_number, **kwargs):
        super().__init__(parent, group_number,  **kwargs)

    def send_command(self, command_name, state='', plm_bytes={}):
        # TODO are the state and plm_bytes needed?
        '''Send an on/off command to a plm group'''
        command = 0x11
        if command_name.lower() == 'off':
            command = 0x13
        plm_bytes = {
            'group': self.group_number,
            'cmd_1': command,
            'cmd_2': 0x00,
        }
        message = PLM_Message(self.parent,
                              device=self.parent,
                              plm_cmd='all_link_send',
                              plm_bytes=plm_bytes)
        message.state_machine = 'all_link_send'
        self.parent._queue_device_msg(message)
        records = self.parent._aldb.get_matching_records({
            'controller': True,
            'group': self.group_number,
            'in_use': True
        })
        # Until all link status is complete, sending any other cmds to PLM
        # will cause it to abandon all link process
        message.seq_lock = True
        message.seq_time = (len(records) + 1) * (87 / 1000 * 6)
        for position in records:
            linked_obj = self.parent._aldb.get_linked_obj(position)
            # Queue a cleanup message on each device, this msg will
            # be cleared from the queue on receipt of a cleanup
            # ack
            # TODO we are not currently handling uncommon alias type
            # cmds
            cmd_str = 'on_cleanup'
            if command == 0x13:
                cmd_str = 'off_cleanup'

            linked_obj.send_command(
                cmd_str, '', {'cmd_2': self.group_number})
