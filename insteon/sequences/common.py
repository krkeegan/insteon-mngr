from insteon.trigger import InsteonTrigger, PLMTrigger


class BaseSequence(object):
    def __init__(self, device):
        self._device = device
        self._success_callback = None
        self._failure_callback = None
        self._complete = False
        self._success = False

    @property
    def success_callback(self):
        return self._success_callback

    @success_callback.setter
    def success_callback(self, callback):
        self._success_callback = callback

    @property
    def failure_callback(self):
        return self._failure

    @failure_callback.setter
    def failure_callback(self, callback):
        self._failure = callback

    @property
    def is_complete(self):
        return self._complete

    @property
    def is_success(self):
        return self._success

    def on_success(self):
        self._complete = True
        self._success = True
        if self.success_callback is not None:
            self.success_callback()

    def on_failure(self):
        self._complete = True
        self._success = False
        if self.failure_callback is not None:
            self._failure()

    def start(self):
        return NotImplemented


class StatusRequest(BaseSequence):
    '''Used to request the status of a device.  The neither cmd_1 nor cmd_2 of the
    return message can be predicted so we just hope it is the next direct_ack that
    we receive'''
    # TODO what would happen if this message was never acked?  Would this
    # trigger remain in waiting and fire the next time we received an ack?
    # should add a maximum timer to the BaseSequence that triggers failure

    def start(self):
        trigger_attributes = {
            'msg_type': 'direct_ack',
            'plm_cmd': 0x50,
            'msg_length': 'standard'
        }
        trigger = InsteonTrigger(device=self._device,
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._process_status_response()
        trigger.name = self._device.dev_addr_str + 'status_request'
        trigger.queue()
        self._device.send_handler.send_command('light_status_request')

    def _process_status_response(self):
        msg = self._device.last_rcvd_msg
        self._device.state = msg.get_byte_by_name('cmd_2')
        aldb_delta = msg.get_byte_by_name('cmd_1')
        if self._device.attribute('aldb_delta') != aldb_delta:
            print('aldb has changed, rescanning')
            self._device.send_handler.query_aldb()
        self.on_success()


class SetALDBDelta(StatusRequest):
    '''Used to get and store the tracking value for the ALDB Delta'''

    def _process_status_response(self):
        msg = self._device.last_rcvd_msg
        self._device.state = msg.get_byte_by_name('cmd_2')
        self._device.set_aldb_delta(msg.get_byte_by_name('cmd_1'))
        print ('cached aldb_delta')
        self.on_success()


class WriteALDBRecord(BaseSequence):
    '''Sequence to write an aldb record to a device.'''
    def __init__(self, device):
        super().__init__(device)
        self._controller = False
        self._linked_device = None
        self._d1 = 0x00
        self._d2 = 0x00
        self._address = None
        self._in_use = True

    @property
    def in_use(self):
        return self._in_use

    @in_use.setter
    def in_use(self, use):
        self._in_use = use

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
    def key(self):
        # pylint: disable=E1305
        ret = None
        if self._address is not None:
            ret = ('{:02x}'.format(self._address[0], 'x').upper() +
                   '{:02x}'.format(self._address[1], 'x').upper())
        return ret

    @key.setter
    def key(self, value):
        msb = int(value[0:2], 16)
        lsb = int(value[2:4], 16)
        self._address = bytearray([msb, lsb])

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

    def _bind_to_address(self):
        if self._address is None:
            self.address = self.address

    def _compiled_record(self):
        msg_attributes = {
            'msb': self.address[0],
            'lsb': self.address[1]
        }
        if not self.in_use:
            msg_attributes['link_flags'] = 0x02
            msg_attributes['group'] = 0x00
            msg_attributes['data_1'] = 0x00
            msg_attributes['data_2'] = 0x00
            msg_attributes['data_3'] = 0x00
            msg_attributes['dev_addr_hi'] = 0x00
            msg_attributes['dev_addr_mid'] = 0x00
            msg_attributes['dev_addr_low'] = 0x00
        elif self.controller:
            msg_attributes['link_flags'] = 0xE2
            msg_attributes['group'] = self._device.group_number
            msg_attributes['data_1'] = self.data1  # hops I think
            msg_attributes['data_2'] = self.data2  # unkown always 0x00
            # group of controller device base_group for 0x01, 0x00 issue
            msg_attributes['data_3'] = self._device.group_number
            msg_attributes['dev_addr_hi'] = self._linked_device.dev_addr_hi
            msg_attributes['dev_addr_mid'] = self._linked_device.dev_addr_mid
            msg_attributes['dev_addr_low'] = self._linked_device.dev_addr_low
        else:
            msg_attributes['link_flags'] = 0xA2
            msg_attributes['group'] = self._linked_device.group_number
            msg_attributes['data_1'] = self.data1  # on level
            msg_attributes['data_2'] = self.data2  # ramp rate
            # group of responder, i1 = 00, i2 = 01
            msg_attributes['data_3'] = self._device.group_number
            msg_attributes['dev_addr_hi'] = self._linked_device.dev_addr_hi
            msg_attributes['dev_addr_mid'] = self._linked_device.dev_addr_mid
            msg_attributes['dev_addr_low'] = self._linked_device.dev_addr_low
        return msg_attributes

    def start(self):
        '''Starts the sequence to write the aldb record'''
        if self.linked_device is None and self.in_use:
            print('error no linked_device defined')
        else:
            status_sequence = StatusRequest(self._device)
            callback = lambda: self._perform_write()  # pylint: disable=W0108
            status_sequence.success_callback = callback
            status_sequence.start()

    def _perform_write(self):
        return NotImplemented


class AddPLMtoDevice(BaseSequence):
    def start(self):
        # Put the PLM in Linking Mode
        # queues a message on the PLM
        message = self._device.plm.create_message('all_link_start')
        plm_bytes = {
            'link_code': 0x01,
            'group': 0x00,
        }
        message.insert_bytes_into_raw(plm_bytes)
        message.plm_success_callback = self._add_plm_to_dev_link_step2
        message.msg_failure_callback = self._add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self._device.plm.queue_device_msg(message)

    def _add_plm_to_dev_link_step2(self):
        # Put Device in linking mode
        message = self._device.send_handler.create_message('enter_link_mode')
        dev_bytes = {
            'cmd_2': 0x00
        }
        message.insert_bytes_into_raw(dev_bytes)
        message.insteon_msg.device_success_callback = (
            self._add_plm_to_dev_link_step3
        )
        message.msg_failure_callback = self._add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self._device.queue_device_msg(message)

    def _add_plm_to_dev_link_step3(self):
        trigger_attributes = {
            'from_addr_hi': self._device.dev_addr_hi,
            'from_addr_mid': self._device.dev_addr_mid,
            'from_addr_low': self._device.dev_addr_low,
            'link_code': 0x01,
            'plm_cmd': 0x53
        }
        trigger = PLMTrigger(plm=self._device.plm,
                             attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._add_plm_to_dev_link_step4()
        trigger.name = self._device.dev_addr_str + 'add_plm_step_3'
        trigger.queue()
        print('device in linking mode')

    def _add_plm_to_dev_link_step4(self):
        print('plm->device link created')
        self._device.plm.remove_state_machine('link plm->device')
        self._device.remove_state_machine('link plm->device')
        self.on_success()
        self._device.send_handler.initialize_device()

    def _add_plm_to_dev_link_fail(self):
        print('Error, unable to create plm->device link')
        self._device.plm.remove_state_machine('link plm->device')
        self._device.remove_state_machine('link plm->device')
        self.on_failure()


class InitializeDevice(BaseSequence):
    def start(self):
        if self._device.attribute('engine_version') is None:
            self._device.send_handler.get_engine_version()
        else:
            self._init_step_2()

    def _init_step_2(self):
        # TODO consider whether getting status is always necessary or desired
        # results in get engine version or get dev_cat always causing a status
        # request
        if (self._device.dev_cat is None or
                self._device.sub_cat is None or
                self._device.firmware is None):
            trigger_attributes = {
                'cmd_1': 0x01,
                'insteon_msg_type': 'broadcast'
            }
            trigger = InsteonTrigger(device=self._device,
                                     attributes=trigger_attributes)
            trigger.trigger_function = lambda: self._device.send_handler.get_status()
            trigger.name = self._device.dev_addr_str + 'init_step_2'
            trigger.queue()
            self._device.send_handler.get_device_version()
        else:
            self._device.update_device_classes()
            self._device.send_handler.get_status()
