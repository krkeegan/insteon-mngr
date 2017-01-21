class GenericMsgHandler(object):
    '''Provides the generic message handling that does not conflict with
    any Insteon devices.  Devices with distinct messages and needs should
    create their own message handler class that inherits and overrides the
    necessary elements'''
    def __init__(self, device):
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

###################################################
#
# Message Processing Functions
#
###################################################

    def _ext_aldb_rcvd(self, msg):
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
