from insteon.trigger import InsteonTrigger
from insteon.sequences.common import SetALDBDelta, BaseSequence

class ScanDeviceALDBi2(BaseSequence):
    def start(self):
        self._device.aldb.clear_all_records()
        dev_bytes = {'msb': 0x00, 'lsb': 0x00}
        message = self._device.send_handler.create_message('read_aldb')
        message.insert_bytes_into_raw(dev_bytes)
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)
        # It would be nice to link the trigger to the msb and lsb, but we
        # don't technically have that yet at this point
        trigger_attributes = {'msg_type': 'direct'}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='read_aldb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._i2_next_aldb()
        trigger_name = self._device.dev_addr_str + 'query_aldb'
        self._device.plm.trigger_mngr.add_trigger(trigger_name, trigger)

    def _i2_next_aldb(self):
        rcvd_handler = self._device._rcvd_handler
        msb = rcvd_handler.last_rcvd_msg.get_byte_by_name('usr_3')
        lsb = rcvd_handler.last_rcvd_msg.get_byte_by_name('usr_4')
        aldb_key = self._device.aldb.get_aldb_key(msb, lsb)
        if self._device.aldb.is_last_aldb(aldb_key):
            self._device.remove_state_machine('query_aldb')
            self._device.aldb.print_records()
            aldb_sequence = SetALDBDelta(self._device)
            aldb_sequence.success_callback = self.success_callback
            aldb_sequence.failure_callback = self.failure_callback
            aldb_sequence.start()
        else:
            dev_bytes = self._device.aldb.get_next_aldb_address(msb, lsb)
            self._device.send_handler.i2_get_aldb(dev_bytes, 'query_aldb')
            trigger_attributes = {
                'usr_3': dev_bytes['msb'],
                'usr_4': dev_bytes['lsb'],
                'msg_type': 'direct'
            }
            trigger = InsteonTrigger(device=self._device,
                                     command_name='read_aldb',
                                     attributes=trigger_attributes)
            trigger.trigger_function = lambda: self._i2_next_aldb()
            trigger_name = self._device.dev_addr_str + 'query_aldb'
            self._device.plm.trigger_mngr.add_trigger(trigger_name, trigger)


class WriteALDBRecordi2(BaseSequence):
    def write_record(self):
        pass
        # check if aldb delta is accurate
        # requires running StatusRequest but needs a success and failure
        # callback

    def perform_write(self):
        pass
        # do the stuff

    def write_failure(self):
        pass
        #
