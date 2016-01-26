from insteon.trigger import InsteonTrigger
from insteon.sequences.common import SetALDBDelta, BaseSequence

class ScanDeviceALDBi1(BaseSequence):
    def start(self):
        self._device.aldb.clear_all_records()
        self._i1_start_aldb_entry_query(0x0F, 0xF8)

    def _i1_start_aldb_entry_query(self, msb, lsb):
        # TODO do we need to add device ack as a field too? wouldn't a nack
        # cause this to trip?
        trigger_attributes = {'cmd_2': msb}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='set_address_msb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._send_peek_request(lsb)
        self._device.plm.trigger_mngr.add_trigger(self._device.dev_addr_str +
                                                  'query_aldb',
                                                  trigger)
        message = self._device.send_handler.create_message('set_address_msb')
        message.insert_bytes_into_raw({'msb': msb})
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)

    def _get_byte_address(self):
        lsb = self._device.last_sent_msg.get_byte_by_name('cmd_2')
        msb_msg = self._device.search_last_sent_msg(
            insteon_cmd='set_address_msb')
        msb = msb_msg.get_byte_by_name('cmd_2')
        aldb_key = self._device.aldb.get_aldb_key(msb, lsb)
        if self._device.aldb.is_last_aldb(aldb_key):
            self._device.aldb.print_records()
            self._device.remove_state_machine('query_aldb')
            aldb_sequence = SetALDBDelta(self._device)
            aldb_sequence.success_callback = self.success_callback
            aldb_sequence.failure_callback = self.failure_callback
            aldb_sequence.start()
        else:
            dev_bytes = self._device.aldb.get_next_aldb_address(msb, lsb)
            send_handler = self._device.send_handler
            if msb != dev_bytes['msb']:
                send_handler.i1_start_aldb_entry_query(dev_bytes['msb'],
                                                       dev_bytes['lsb'])
            else:
                self._send_peek_request(dev_bytes['lsb'])

    def _send_peek_request(self, lsb):
        trigger = InsteonTrigger(device=self._device,
                                 command_name='peek_one_byte')
        trigger.trigger_function = lambda: self._get_byte_address()
        self._device.plm.trigger_mngr.add_trigger(self._device.dev_addr_str +
                                                  'query_aldb',
                                                  trigger)
        message = self._device.send_handler.create_message('peek_one_byte')
        message.insert_bytes_into_raw({'lsb': lsb})
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)
