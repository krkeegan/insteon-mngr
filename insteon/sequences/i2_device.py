from insteon.trigger import InsteonTrigger
from insteon.sequences.common import SetALDBDelta, BaseSequence, StatusRequest


class ScanDeviceALDBi2(BaseSequence):
    '''Sequence object used for scanning the All link database of an i2
    device'''
    def start(self):
        self._device.aldb.clear_all_records()
        dev_bytes = {'msb': 0x00, 'lsb': 0x00}
        message = self._device.send_handler.create_message('read_aldb')
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
            # pylint: disable=W0108
            trigger = InsteonTrigger(device=self._device,
                                     command_name='read_aldb',
                                     attributes=trigger_attributes)
            trigger.trigger_function = lambda: self._i2_next_aldb()
            trigger_name = self._device.dev_addr_str + 'query_aldb'
            self._device.plm.trigger_mngr.add_trigger(trigger_name, trigger)


class WriteALDBRecordi2(BaseSequence):
    '''Sequence to write an aldb record to an i2 device.'''
    def __init__(self, device):
        super().__init__(device)
        self._controller = False
        self._linked_device = None
        self._d1 = 0x00
        self._d2 = 0x00
        self._d3 = 0x00

    @property
    def controller(self):
        '''If true, this device is the controller, false the responder.
        Defaults to false.'''
        return self._controller

    @controller.setter
    def controller(self, boolean):
        self._controller = boolean

    @property
    def linked_device(self):
        '''Required. The device on the other end of this link.'''
        return self._linked_device

    @linked_device.setter
    def linked_device(self, device):
        self._linked_device = device

    @property
    def data1(self):
        '''The device specific byte to write to the data1 location defaults
        to 0x00.'''
        return self._d1

    @data1.setter
    def data1(self, byte):
        self._d1 = byte

    @property
    def data2(self):
        '''The device specific byte to write to the data2 location defaults
        to 0x00.'''
        return self._d2

    @data2.setter
    def data2(self, byte):
        self._d2 = byte

    def start(self):
        '''Starts the sequence to write the aldb record'''
        if self.linked_device is None:
            print('error no linked_device defined')
        else:
            status_sequence = StatusRequest(self._device)
            callback = lambda: self._perform_write()  # pylint: disable=W0108
            status_sequence.success_callback = callback
            status_sequence.start()

    def _perform_write(self):
        # TODO need to enable update a particular key
        key = self._device.aldb.get_first_empty_addr()
        msg_attributes = {
            'msb': int(key[0:2], 16),
            'lsb': int(key[2:4], 16),
            'dev_addr_hi': self._linked_device.dev_addr_hi,
            'dev_addr_mid': self._linked_device.dev_addr_mid,
            'dev_addr_low': self._linked_device.dev_addr_low
        }
        if self.controller:
            msg_attributes['link_flags'] = 0xE2
            msg_attributes['group'] = self._device.group
            msg_attributes['data_1'] = self.data1  # hops I think
            msg_attributes['data_2'] = self.data2  # unkown always 0x00
            # group of responding device
            msg_attributes['data_3'] = self._linked_device.group
        else:
            msg_attributes['link_flags'] = 0xA2
            msg_attributes['group'] = self._linked_device.group
            msg_attributes['data_1'] = self.data1  # on level
            msg_attributes['data_2'] = self.data2  # ramp rate
            # group of responder, i1 = 00, i2 = 01
            msg_attributes['data_3'] = self._device.get_responder_data3()
        trigger_attributes = {
            'cmd_2': 0x00,
            'msg_length': 'standard'
        }
        trigger = InsteonTrigger(device=self._device,
                                 command_name='write_aldb',
                                 attributes=trigger_attributes)
        aldb_sequence = SetALDBDelta(self._device)
        trigger.trigger_function = lambda: aldb_sequence.start()
        trigger_name = self._device.dev_addr_str + 'write_aldb'
        self._device.plm.trigger_mngr.add_trigger(trigger_name, trigger)
        msg = self._device.send_handler.create_message('write_aldb')
        msg.insert_bytes_into_raw(msg_attributes)
        self._device.queue_device_msg(msg)

    def _write_failure(self):
        if self.failure_callback is not None:
            self._failure()
