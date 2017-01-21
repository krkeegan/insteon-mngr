from insteon.helpers import BYTE_TO_HEX


class GenericMsgHandler(object):
    '''Provides the generic message handling that does not conflict with
    any Insteon devices.  Devices with distinct messages and needs should
    create their own message handler class that inherits and overrides the
    necessary elements'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device

###################################################
#
# Dispatchers
#
###################################################

    def dispatch_direct(self, msg):
        '''Dispatchs an incomming direct message to the correct function.
        Only extended messages are processed because the modem handles
        all standard direct messages.

        Returns
        True = a function successfully processed the message
        False = no function successfully processed the message'''
        ret = False
        if msg.insteon_msg.msg_length == 'extended':
            cmd_byte = msg.get_byte_by_name('cmd_1')
            if cmd_byte == 0x2F:
                ret = True
                self._ext_aldb_rcvd(msg)
        return ret

    def dispatch_status_resp(self, msg):
        '''Checks to see if the device is expecting a status response, if it
        is, then treat this message as such'''
        ret = False
        if (self._device.last_sent_msg.insteon_msg.device_cmd_name ==
                'light_status_request'):
            self._status_response(msg)
            ret = True
        return ret

    def dispatch_direct_ack(self, msg):
        '''processes an incomming direct ack message'''
        ret = False
        cmd_byte = msg.get_byte_by_name('cmd_1')
        if cmd_byte == 0X0D:
            version = msg.get_byte_by_name('cmd_2')
            self._device.set_engine_version(version)
            ret = True
        elif cmd_byte == 0x28:
            ret = self._ack_set_msb(msg)
        elif cmd_byte == 0x2B:
            ret = True
            self._ack_peek_aldb(msg)
        elif cmd_byte == 0x2F:
            ret = self._ext_aldb_ack(msg)
        return ret

###################################################
#
# Message Processing Functions
#
###################################################

    def _ext_aldb_rcvd(self, msg):
        '''Sets the device_ack flag, while not specifically an ack'''
        if (self._device.last_sent_msg.insteon_msg.device_prelim_ack is True and
                self._device.last_sent_msg.insteon_msg.device_ack is False):
            last_msg = self._device.search_last_sent_msg(insteon_cmd='read_aldb')
            req_msb = last_msg.get_byte_by_name('msb')
            req_lsb = last_msg.get_byte_by_name('lsb')
            msg_msb = msg.get_byte_by_name('usr_3')
            msg_lsb = msg.get_byte_by_name('usr_4')
            if ((req_lsb == msg_lsb and req_msb == msg_msb) or
                    (req_lsb == 0x00 and req_msb == 0x00)):
                aldb_entry = bytearray([
                    msg.get_byte_by_name('usr_6'),
                    msg.get_byte_by_name('usr_7'),
                    msg.get_byte_by_name('usr_8'),
                    msg.get_byte_by_name('usr_9'),
                    msg.get_byte_by_name('usr_10'),
                    msg.get_byte_by_name('usr_11'),
                    msg.get_byte_by_name('usr_12'),
                    msg.get_byte_by_name('usr_13')
                ])
                self._device.aldb.edit_record(self._device.aldb.get_aldb_key(msg_msb, msg_lsb),
                                              aldb_entry)
                self._device.last_sent_msg.insteon_msg.device_ack = True
        else:
            msg.allow_trigger = False
            print('received spurious ext_aldb record')

    def _status_response(self, msg):
        print('was status response')
        self._device.check_aldb_delta(msg.get_byte_by_name('cmd_1'))
        self._device.set_cached_state(msg.get_byte_by_name('cmd_2'))
        self._device.last_sent_msg.insteon_msg.device_ack = True

    def _ack_set_msb(self, msg):
        if (self._device.last_sent_msg.get_byte_by_name('cmd_2') ==
                msg.get_byte_by_name('cmd_2')):
            ret = True
        else:
            ret = False
        return ret

    def _ack_peek_aldb(self, msg):
        # TODO this seems like way too much work in the ALDB to be done here
        # I think we need to move this logic to a public function in ALDB
        lsb = self._device.last_sent_msg.get_byte_by_name('cmd_2')
        msb_msg = self._device.search_last_sent_msg(insteon_cmd='set_address_msb')
        msb = msb_msg.get_byte_by_name('cmd_2')
        if (lsb % 8) == 0:
            self._device.aldb.edit_record(
                self._device.aldb.get_aldb_key(msb, lsb), bytearray(8))
        self._device.aldb.edit_record_byte(
            self._device.aldb.get_aldb_key(msb, lsb),
            lsb % 8,
            msg.get_byte_by_name('cmd_2')
        )
        if self._device.aldb.is_last_aldb(self._device.aldb.get_aldb_key(msb, lsb)):
            # this is the last entry on this device
            records = self._device.aldb.get_all_records()
            for key in sorted(records):
                print(key, ":", BYTE_TO_HEX(records[key]))
            self._device.remove_state_machine('query_aldb')
            self._device.send_command('light_status_request', 'set_aldb_delta')
        elif self._device.aldb.is_empty_aldb(self._device.aldb.get_aldb_key(msb, lsb)):
            # this is an empty record
            print('empty record')
            lsb = lsb - (8 + (lsb % 8))
            self._device.aldb.peek_aldb(lsb)
        elif lsb == 7:
            # Change MSB
            msb -= 1
            lsb = 0xF8
            self._device.aldb.i1_start_aldb_entry_query(msb, lsb)
        elif (lsb % 8) == 7:
            lsb -= 15
            self._device.aldb.peek_aldb(lsb)
        else:
            lsb += 1
            self._device.aldb.peek_aldb(lsb)
        return True # Is there a scenario in which we return False?

    def _ext_aldb_ack(self, msg):
        # pylint: disable=W0613
        # msg is passed to all similar functions
        # TODO consider adding more time for following message to arrive
        if (self._device.last_sent_msg.insteon_msg.device_prelim_ack is False and
                self._device.last_sent_msg.insteon_msg.device_ack is False):
            if self._device.last_sent_msg.get_byte_by_name('usr_2') == 0x00:
                # When reading ALDB a subsequent ext msg will contain record
                self._device.last_sent_msg.insteon_msg.device_prelim_ack = True
            else:
                self._device.last_sent_msg.insteon_msg.device_ack = True
        else:
            print('received spurious ext_aldb_ack')
        return False  # Never set ack
