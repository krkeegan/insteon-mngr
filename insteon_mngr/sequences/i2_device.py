from insteon_mngr.trigger import InsteonTrigger
from insteon_mngr.sequences.common import SetALDBDelta, BaseSequence, WriteALDBRecord


class ScanDeviceALDBi2(BaseSequence):
    '''Sequence object used for scanning the All link database of an i2
    device'''
    def __init__(self, device=None):
        super().__init__()
        self._device = device

    def start(self):
        self._device.aldb.clear_all_records()
        dev_bytes = {'msb': 0x00, 'lsb': 0x00}
        message = self._device.create_message('read_aldb')
        message.insert_bytes_into_raw(dev_bytes)
        message.state_machine = 'query_aldb'
        self._device.queue_device_msg(message)
        # It would be nice to link the trigger to the msb and lsb, but we
        # don't technically have that yet at this point
        # pylint: disable=W0108
        trigger_attributes = {'msg_type': 'direct'}
        trigger = InsteonTrigger(device=self._device,
                                 command_name='read_aldb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._i2_next_aldb()
        trigger.name = self._device.dev_addr_str + 'query_aldb'
        trigger.queue()

    def _i2_next_aldb(self):
        msb = self._device.last_rcvd_msg.get_byte_by_name('usr_3')
        lsb = self._device.last_rcvd_msg.get_byte_by_name('usr_4')
        aldb_key = self._device.aldb.get_aldb_key(msb, lsb)
        if self._device.aldb.get_record(aldb_key).is_last_aldb():
            del self._device.queue['query_aldb']
            self._device.aldb.print_records()
            aldb_sequence = SetALDBDelta(group=self._device.base_group)
            aldb_sequence.add_success_callback(lambda: self._on_success())
            aldb_sequence.add_failure_callback(lambda: self._on_failure())
            aldb_sequence.start()
        else:
            dev_bytes = self._device.aldb.get_next_aldb_address(msb, lsb)
            self._device.send_handler.i2_get_aldb(dev_bytes, 'query_aldb')
            trigger_attributes = {
                'usr_3': dev_bytes['msb'],
                'usr_4': dev_bytes['lsb'],
                'msg_type': 'direct'
            }
            # pylint: disable=W0108
            trigger = InsteonTrigger(device=self._device,
                                     command_name='read_aldb',
                                     attributes=trigger_attributes)
            trigger.trigger_function = lambda: self._i2_next_aldb()
            trigger.name = self._device.dev_addr_str + 'query_aldb'
            trigger.queue()


class WriteALDBRecordi2(WriteALDBRecord):
    def _perform_write(self):
        super()._perform_write()
        msg_attributes = self._compiled_record()
        trigger_attributes = {
            'cmd_2': 0x00,
            'msg_length': 'standard',
            'plm_cmd': 0x50
        }
        trigger = InsteonTrigger(device=self._group.device,
                                 command_name='write_aldb',
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._save_record()
        trigger.name = self._group.device.dev_addr_str + 'write_aldb'
        trigger.queue()
        msg = self._group.device.create_message('write_aldb')
        msg.insert_bytes_into_raw(msg_attributes)
        self._group.device.queue_device_msg(msg)

    def _save_record(self):
        aldb_entry = bytearray([
            self._compiled_record()['link_flags'],
            self._compiled_record()['group'],
            self._compiled_record()['dev_addr_hi'],
            self._compiled_record()['dev_addr_mid'],
            self._compiled_record()['dev_addr_low'],
            self._compiled_record()['data_1'],
            self._compiled_record()['data_2'],
            self._compiled_record()['data_3']
        ])
        record = self._group.device.aldb.get_record(
            self._group.device.aldb.get_aldb_key(
                self.address[0],
                self.address[1]
            )
        )
        record.edit_record(aldb_entry)
        self._on_success()

    def _write_failure(self):
        self._on_failure()
