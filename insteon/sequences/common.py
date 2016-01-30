from insteon.trigger import InsteonTrigger


class BaseSequence(object):
    def __init__(self, device):
        self._device = device
        self._success = None
        self._failure = None

    @property
    def success_callback(self):
        return self._success

    @success_callback.setter
    def success_callback(self, callback):
        self._success = callback

    @property
    def failure_callback(self):
        return self._failure

    @failure_callback.setter
    def failure_callback(self, callback):
        self._failure = callback

    def start(self):
        return NotImplemented

class StatusRequest(BaseSequence):
    '''Used to request the status of a device.  The neither cmd_1 nor cmd_2 of the
    return message can be predicted so we just hope it is the next direct_ack that
    we receive'''
    def start(self):
        trigger_attributes = {
            'msg_type': 'direct_ack',
            'plm_cmd': 0x50,
            'msg_length': 'standard'
        }
        trigger = InsteonTrigger(device=self._device,
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._process_status_response()
        self._device.plm.trigger_mngr.add_trigger(self._device.dev_addr_str +
                                                  'status_request',
                                                  trigger)
        self._device.send_handler.send_command('light_status_request')

    def _process_status_response(self):
        msg = self._device._rcvd_handler.last_rcvd_msg
        self._device.set_cached_state(msg.get_byte_by_name('cmd_2'))
        aldb_delta = msg.get_byte_by_name('cmd_1')
        if self._device.attribute('aldb_delta') != aldb_delta:
            print('aldb has changed, rescanning')
            self._device.send_handler.query_aldb()
        elif self.success_callback is not None:
            self._success()

class SetALDBDelta(StatusRequest):
    '''Used to get and store the tracking value for the ALDB Delta'''

    def _process_status_response(self):
        msg = self._device._rcvd_handler.last_rcvd_msg
        self._device.set_cached_state(msg.get_byte_by_name('cmd_2'))
        self._device.set_aldb_delta(msg.get_byte_by_name('cmd_1'))
        print ('cached aldb_delta')
        if self.success_callback is not None:
            self._success()


class WriteALDBRecord(BaseSequence):
    '''Sequence to write an aldb record to a device.'''
    def __init__(self, device):
        super().__init__(device)
        self._controller = False
        self._linked_device = None
        self._d1 = 0x00
        self._d2 = 0x00
        self._address = None

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

    @property
    def address(self):
        '''The address to write to, as a bytearray, if not specified will use
        the first empty address.'''
        ret = self._address
        if self._address is None:
            key = self._device.aldb.get_first_empty_addr()
            msb = int(key[0:2], 16)
            lsb = int(key[2:4], 16)
            ret = bytearray([msb, lsb])
        return ret

    @address.setter
    def address(self, address):
        self._address = address

    def _compiled_record(self):
        msg_attributes = {
            'msb': self.address[0],
            'lsb': self.address[1],
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
        return msg_attributes

    def start(self):
        '''Starts the sequence to write the aldb record'''
        if self.linked_device is None:
            print('error no linked_device defined')
        else:
            status_sequence = StatusRequest(self._device)
            callback = lambda: self._perform_write()  # pylint: disable=W0108
            status_sequence.success_callback = callback
            status_sequence.start()
