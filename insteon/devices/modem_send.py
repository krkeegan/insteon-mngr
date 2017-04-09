from insteon.devices import BaseSendHandler
from insteon.plm_message import PLM_Message
from insteon.sequences import WriteALDBRecordModem

class ModemSendHandler(BaseSendHandler):
    '''Provides the generic command handling for the Modem.  This is a
    seperate class for consistence with devices.'''
    def send_command(self, command, state=''):
        message = self.create_message(command)
        message.state_machine = state
        self._device.queue_device_msg(message)

    def create_message(self, command):
        message = PLM_Message(
            self._device, device=self._device,
            plm_cmd=command)
        return message

    # ALDB Functions
    #######################

    def create_responder_link(self, linked_device):
        message = self.create_message('all_link_manage_rec')
        dev_bytes = {
            'link_flags': 0xA2,
            'group': linked_device.group,
            'dev_addr_hi': linked_device.dev_addr_hi,
            'dev_addr_mid': linked_device.dev_addr_mid,
            'dev_addr_low': linked_device.dev_addr_low,
        }
        records = self._device.aldb.get_matching_records(dev_bytes)
        ctrl_code = 0x20
        if (len(records) == 0):
            ctrl_code = 0x41
        dev_bytes.update({
            'ctrl_code': ctrl_code,
            'data_1': 0x00,  # D1-3 are 0x00 for plm responder
            'data_2': 0x00,
            'data_3': 0x00
        })
        message.insert_bytes_into_raw(dev_bytes)
        self._device.queue_device_msg(message)

    def create_controller_link(self, linked_device):
        message = self.create_message('all_link_manage_rec')
        dev_bytes = {
            'link_flags': 0xE2,
            'group': self._device.group,
            'dev_addr_hi': linked_device.dev_addr_hi,
            'dev_addr_mid': linked_device.dev_addr_mid,
            'dev_addr_low': linked_device.dev_addr_low,
        }
        records = self._device.aldb.get_matching_records(dev_bytes)
        ctrl_code = 0x20
        if (len(records) == 0):
            ctrl_code = 0x40
        dev_bytes.update({
            'ctrl_code': ctrl_code,
            'data_1': linked_device.dev_cat,
            'data_2': linked_device.sub_cat,
            'data_3': linked_device.firmware
        })
        message.insert_bytes_into_raw(dev_bytes)
        self._device.queue_device_msg(message)

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

    def delete_record(self, key=None):
        link_sequence = WriteALDBRecordModem(self._device)
        link_sequence.key = key
        link_sequence.in_use = False
        return link_sequence

    def query_aldb(self):
        '''Queries the PLM for a list of the link records saved on
        the PLM and stores them in the cache'''
        self._device.aldb.clear_all_records() #TODO is this needed?
        self.send_command('all_link_first_rec', 'query_aldb')
