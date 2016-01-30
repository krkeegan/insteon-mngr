

class GenericRcvdHandler(object):
    '''Provides the generic message handling that does not conflict with
    any Insteon devices.  Devices with distinct messages and needs should
    create their own message handler class that inherits and overrides the
    necessary elements'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device
        self._last_rcvd_msg = None

    ###################################################
    #
    # attributes
    #
    ###################################################

    @property
    def last_rcvd_msg(self):
        return self._last_rcvd_msg

    @last_rcvd_msg.setter
    def last_rcvd_msg(self, msg):
        self._last_rcvd_msg = msg

    ###################################################
    #
    # Dispatchers
    #
    ###################################################

    def dispatch_msg_rcvd(self, msg):
        '''Selects the proper message path based on the message type.'''
        self.last_rcvd_msg = msg
        if msg.insteon_msg.message_type == 'direct':
            if not self._dispatch_direct(msg):
                print('unhandled direct message, perhaps dev_cat is wrong')
        elif msg.insteon_msg.message_type == 'direct_ack':
            self._process_direct_ack(msg)
        elif msg.insteon_msg.message_type == 'direct_nack':
            self._process_direct_nack(msg)
        elif msg.insteon_msg.message_type == 'broadcast':
            self._dispatch_broadcast(msg)
        elif msg.insteon_msg.message_type == 'alllink_cleanup_ack':
            self._process_alllink_cleanup(msg)

    def _dispatch_direct(self, msg):
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

    def is_status_resp(self):
        '''Checks to see if the device is expecting a status response'''
        ret = False
        if (self._device.last_sent_msg.insteon_msg.device_cmd_name ==
                'light_status_request'):
            print('was status response')
            ret = True
        return ret

    def _process_direct_ack(self, msg):
        '''processes an incomming direct ack message, sets the
        allow_tigger flags and device_acks flags'''
        if self.is_status_resp():
            self._device.last_sent_msg.insteon_msg.device_ack = True
        elif not self._is_valid_direct_resp(msg):
            msg.allow_trigger = False
        elif self._dispatch_direct_ack(msg) is False:
            msg.allow_trigger = False
        else:
            self._device.last_sent_msg.insteon_msg.device_ack = True

    def _is_valid_direct_resp(self, msg):
        ret = True
        if (self._device.last_sent_msg.get_byte_by_name('cmd_1') !=
                msg.get_byte_by_name('cmd_1')):
            print('unexpected cmd_1 ignoring')
            ret = False
        elif self._device.last_sent_msg.plm_ack is not True:
            print('ignoring a device response received before PLM ack')
            ret = False
        elif self._device.last_sent_msg.insteon_msg.device_ack is not False:
            print('ignoring an unexpected device response')
            ret = False
        return ret

    def _dispatch_direct_ack(self, msg):
        '''processes an incomming direct ack message'''
        ret = False
        cmd_byte = msg.get_byte_by_name('cmd_1')
        if cmd_byte == 0X0D:
            version = msg.get_byte_by_name('cmd_2')
            self._device.set_engine_version(version)
            ret = True
        elif cmd_byte == 0x10:
            ret = self._common_prelim_ack(msg)
        elif cmd_byte == 0x28:  # set_address_msb
            ret = self._ack_set_msb(msg)
        elif cmd_byte == 0x29:  # poke_one_byte
            ret = True
        elif cmd_byte == 0x2B:  # peek_one_byte
            ret = True
            self._ack_peek_aldb(msg)
        elif cmd_byte == 0x2F:
            ret = self._ext_aldb_ack(msg)
        return ret

    def _process_direct_nack(self, msg):
        '''processes an incomming direct nack message'''
        if self._is_valid_direct_resp(msg):
            self._dispatch_direct_nack(msg)

    def _dispatch_direct_nack(self, msg):
        engine_version = self._device.attribute('engine_version')
        if (engine_version == 0x02 or engine_version is None):
            cmd_2 = msg.get_byte_by_name('cmd_2')
            if cmd_2 == 0xFF:
                print('nack received, senders ID not in database')
                self._device.attribute('engine_version', 0x02)
                self._device.last_sent_msg.insteon_msg.device_ack = True
                self._device.remove_state_machine(
                    self._device.last_sent_msg.state_machine)
                print('creating plm->device link')
                self._device.add_plm_to_dev_link()
            elif cmd_2 == 0xFE:
                print('nack received, no load')
                self._device.attribute('engine_version', 0x02)
                self._device.last_sent_msg.insteon_msg.device_ack = True
            elif cmd_2 == 0xFD:
                print('nack received, checksum is incorrect, resending')
                self._device.attribute('engine_version', 0x02)
                self._device.plm.wait_to_send = 1
                self._device._resend_msg(self._device.last_sent_msg)
            elif cmd_2 == 0xFC:
                print('nack received, Pre nack in case database search ',
                      'takes too long')
                self._device.attribute('engine_version', 0x02)
                self._device.last_sent_msg.insteon_msg.device_ack = True
            elif cmd_2 == 0xFB:
                print('nack received, illegal value in command')
                self._device.attribute('engine_version', 0x02)
                self._device.last_sent_msg.insteon_msg.device_ack = True
            else:
                print('device nack`ed the last command, no further ',
                      'details, resending')
                self._device.plm.wait_to_send = 1
                self._device._resend_msg(self._device.last_sent_msg)
        else:
            print('device nack`ed the last command, resending')
            self._device.plm.wait_to_send = 1
            self._device._resend_msg(self._device.last_sent_msg)

    def _dispatch_broadcast(self, msg):
        cmd_byte = msg.get_byte_by_name('cmd_1')
        if cmd_byte == 0X01:
            self._set_button_responder(msg)
        else:
            print('rcvd broadcast message of unknown type')

    def _process_alllink_cleanup(self,msg):
        # TODO is this actually received??  isn't the modem the only one who
        # get this message and doesn't it convert these to a special PLM Msg?
        # TODO set state of the device based on cmd acked
        # Clear queued cleanup messages if they exist
        self._device.remove_cleanup_msgs(msg)
        if (self._device.last_sent_msg and
                self._device.last_sent_msg.get_byte_by_name('cmd_1') ==
                msg.get_byte_by_name('cmd_1') and
                self._device.last_sent_msg.get_byte_by_name('cmd_2') ==
                msg.get_byte_by_name('cmd_2')):
            # Only set ack if this was sent by this device
            self._device.last_sent_msg.insteon_msg.device_ack = True

    ###################################################
    #
    # Message Processing Functions
    #
    ###################################################

    def _ext_aldb_ack(self, msg):
        # pylint: disable=W0613
        # msg is passed to all similar functions
        # TODO consider adding more time for following message to arrive
        last_sent_msg = self._device.last_sent_msg
        if (last_sent_msg.insteon_msg.device_prelim_ack is False and
                last_sent_msg.insteon_msg.device_ack is False):
            if self._device.last_sent_msg.get_byte_by_name('usr_2') == 0x00:
                # When reading ALDB a subsequent ext msg will contain record
                self._device.last_sent_msg.insteon_msg.device_prelim_ack = True
            else:
                self._device.last_sent_msg.insteon_msg.device_ack = True
        else:
            print('received spurious ext_aldb_ack')
        return False  # Never set ack

    def _ext_aldb_rcvd(self, msg):
        '''Sets the device_ack flag, while not specifically an ack'''
        last_sent_msg = self._device.last_sent_msg
        if (last_sent_msg.insteon_msg.device_prelim_ack is True and
                last_sent_msg.insteon_msg.device_ack is False):
            last_msg = self._device.search_last_sent_msg(
                insteon_cmd='read_aldb')
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
                self._device.aldb.edit_record(self._device.aldb.get_aldb_key(
                                                                msg_msb,
                                                                msg_lsb),
                                              aldb_entry)
                self._device.last_sent_msg.insteon_msg.device_ack = True
        else:
            msg.allow_trigger = False
            print('received spurious ext_aldb record')

    def _ack_set_msb(self, msg):
        '''Returns true if the MSB Byte returned matches what we asked for'''
        if (self._device.last_sent_msg.get_byte_by_name('cmd_2') ==
                msg.get_byte_by_name('cmd_2')):
            ret = True
        else:
            ret = False
        return ret

    def _ack_peek_aldb(self, msg):
        '''Parses out the single ALDB byte and determines the MSB and LSB of the
        Byte.  Calls aldb function to store it'''
        lsb = self._device.last_sent_msg.get_byte_by_name('cmd_2')
        msb_msg = self._device.search_last_sent_msg(
            insteon_cmd='set_address_msb')
        msb = msb_msg.get_byte_by_name('cmd_2')
        byte = msg.get_byte_by_name('cmd_2')
        self._device.aldb.store_peeked_byte(msb, lsb, byte)
        return True  # Is there a scenario in which we return False?

    def _common_prelim_ack(self, msg):
        '''If prelim_ack and device_ack of last sent message are false, sets
        the prelim_ack, otherwise warns of spurious ack.  Always returns
        False'''
        # pylint: disable=W0613
        # msg is passed to all similar functions
        # TODO consider adding more time for following message to arrive
        last_sent_msg = self._device.last_sent_msg
        if (last_sent_msg.insteon_msg.device_prelim_ack is False and
                last_sent_msg.insteon_msg.device_ack is False):
            self._device.last_sent_msg.insteon_msg.device_prelim_ack = True
        else:
            print('received spurious device ack')
        return False  # Never set ack

    def _set_button_responder(self, msg):
        last_insteon_msg = self._device.last_sent_msg.insteon_msg
        if (last_insteon_msg.device_cmd_name == 'id_request' and
                last_insteon_msg.device_prelim_ack is True and
                last_insteon_msg.device_ack is False):
            dev_cat = msg.get_byte_by_name('to_addr_hi')
            sub_cat = msg.get_byte_by_name('to_addr_mid')
            firmware = msg.get_byte_by_name('to_addr_low')
            self._device.set_dev_version(dev_cat, sub_cat, firmware)
            last_insteon_msg.device_ack = True
            print('rcvd, broadcast updated devcat, subcat, and firmware')
        else:
            print('rcvd spurious set button pressed from device')
