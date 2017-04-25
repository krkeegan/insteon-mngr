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

    def delete_record(self, key=None):
        link_sequence = WriteALDBRecordModem(group=self._device.base_group)
        link_sequence.key = key
        link_sequence.in_use = False
        return link_sequence

    def query_aldb(self):
        '''Queries the PLM for a list of the link records saved on
        the PLM and stores them in the cache'''
        self._device.aldb.clear_all_records()
        self.send_command('all_link_first_rec', 'query_aldb')
