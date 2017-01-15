from .helpers import BYTE_TO_HEX


class Insteon_Message(object):

    def __init__(self, parent, **kwargs):
        self._device_ack = False
        self._device_retry = 0
        self._cmd_schema = {}
        self._device_cmd_name = ''
        self._parent = parent
        self._device_success_callback = lambda: None
        # Need to reinitialize the message length??? Extended message
        if 'dev_cmd' in kwargs:
            self._construct_insteon_send(kwargs['dev_cmd'])
        if 'dev_bytes' in kwargs:
            for name, byte in kwargs['dev_bytes'].items():
                self._parent._insert_byte_into_raw(byte, name)

    def _construct_insteon_send(self, dev_cmd):
        if dev_cmd['msg_length'] == 'extended':
            length_array = self._parent._msg_byte_length
            addl_length = length_array[1] - length_array[0]
            self._parent._raw_msg.extend(bytearray(addl_length))
        msg_flags = self._construct_msg_flags(dev_cmd)
        self._parent._insert_byte_into_raw(msg_flags, 'msg_flags')
        self._parent._insert_byte_into_raw(
            self._parent.device.dev_addr_hi, 'to_addr_hi')
        self._parent._insert_byte_into_raw(
            self._parent.device.dev_addr_mid, 'to_addr_mid')
        self._parent._insert_byte_into_raw(
            self._parent.device.dev_addr_low, 'to_addr_low')
        keys = ('cmd_1', 'cmd_2', 'usr_1', 'usr_2',
                'usr_3', 'usr_4', 'usr_5', 'usr_6',
                'usr_7', 'usr_8', 'usr_9', 'usr_10',
                'usr_11', 'usr_12', 'usr_13', 'usr_14')
        for key in keys:
            if key in dev_cmd:
                dev_byte = dev_cmd[key]
                if 'default' in dev_byte:
                    self._parent._insert_byte_into_raw(dev_byte['default'],
                                                       key)
                if 'function' in dev_byte:
                    value = dev_byte['function'](self._parent.device)
                    self._parent._insert_byte_into_raw(value, key)
                if 'name' in dev_byte:
                    self._parent._insteon_attr[dev_byte['name']] = \
                        self._parent.attribute_positions[key]
        self._device_cmd_name = dev_cmd['name']

    def _construct_msg_flags(self, dev_cmd):
        msg_types = {
            'broadcast': 4,
            'direct': 0,
            'direct_ack': 1,
            'direct_nack': 5,
            'alllink_broadcast': 6,
            'alllink_cleanup': 2,
            'alllink_cleanup_ack': 3,
            'alllink_cleanup_nack': 7,
        }
        msg_flags = msg_types[dev_cmd['message_type']]
        msg_flags = msg_flags << 5
        if dev_cmd['msg_length'] == 'extended':
            msg_flags = msg_flags | 16
        hops_left = self._parent.device.smart_hops << 2
        msg_flags = msg_flags | hops_left
        msg_flags = msg_flags | self._parent.device.smart_hops
        return msg_flags

    def _set_i2cs_checksum(self):
        if (self.msg_length == 'extended' and
                self._parent.device.attribute('engine_version') == 0x02):
            checksum = self._calculate_i2cs_checksum()
            self._parent._insert_byte_into_raw(checksum, 'usr_14')
            return

    def _calculate_i2cs_checksum(self):
        # Sum Relevant Bytes
        keys = ('cmd_1', 'cmd_2', 'usr_1', 'usr_2',
                'usr_3', 'usr_4', 'usr_5', 'usr_6',
                'usr_7', 'usr_8', 'usr_9', 'usr_10',
                'usr_11', 'usr_12', 'usr_13')
        bytesum = 0
        for key in keys:
            bytesum += self._parent.get_byte_by_name(key)
        # Flip Bits
        bytesum = ~ bytesum
        # Add 1
        bytesum += 1
        # Truncate to a byte
        bytesum = bytesum & 0b11111111
        return bytesum

    @property
    def valid_i2cs_checksum(self):
        ret = False
        if (self._parent.get_byte_by_name('usr_14') ==
                self._calculate_i2cs_checksum()):
            ret = True
        return ret

    @property
    def device_retry(self):
        return self._device_retry

    @device_retry.setter
    def device_retry(self, count):
        self._device_retry = count

    @property
    def device_cmd_name(self):
        return self._device_cmd_name

    @property
    def message_type(self):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        ret = False
        if msg_flags:
            msg_types = {
                4: 'broadcast',
                0: 'direct',
                1: 'direct_ack',
                5: 'direct_nack',
                6: 'alllink_broadcast',
                2: 'alllink_cleanup',
                3: 'alllink_cleanup_ack',
                7: 'alllink_cleanup_nack'
            }
            message_type = msg_flags & 0b11100000
            message_type = message_type >> 5
            ret = msg_types[message_type]
        return ret

    @property
    def msg_length(self):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        ret = False
        if msg_flags:
            ret = 'standard'
            if msg_flags & 16:
                ret = 'extended'
        return ret

    @property
    def hops_left(self):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        ret = False
        if msg_flags:
            hops_left = msg_flags & 0b00001100
            ret = hops_left >> 2
        return ret

    @hops_left.setter
    def hops_left(self, value):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        if value < 0:
            value = 0
        if value > 3:
            value = 3
        # clear the hops left
        msg_flags = msg_flags & 0b11110011
        # set the hops left
        value = value << 2
        msg_flags = msg_flags | value
        self._parent._insert_byte_into_raw(msg_flags, 'msg_flags')

    @property
    def max_hops(self):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        ret = False
        if msg_flags:
            ret = msg_flags & 0b00000011
        return ret

    @max_hops.setter
    def max_hops(self, value):
        msg_flags = self._parent.get_byte_by_name('msg_flags')
        if value < 0:
            value = 0
        if value > 3:
            value = 3
        # clear the max hops
        msg_flags = msg_flags & 0b11111100
        # set the max hops
        msg_flags = msg_flags | value
        self._parent._insert_byte_into_raw(msg_flags, 'msg_flags')

    @property
    def to_addr_str(self):
        if 'to_addr_hi' in self._parent.attribute_positions:
            byte_pos_hi = self._parent.attribute_positions['to_addr_hi']
            byte_pos_mid = self._parent.attribute_positions['to_addr_mid']
            byte_pos_low = self._parent.attribute_positions['to_addr_low']
            return BYTE_TO_HEX(bytes((self._parent.raw_msg[byte_pos_hi],
                                      self._parent.raw_msg[byte_pos_mid],
                                      self._parent.raw_msg[byte_pos_low],
                                      )))
        else:
            return False

    @property
    def from_addr_str(self):
        if 'to_addr_hi' in self._parent.attribute_positions:
            byte_pos_hi = self._parent.attribute_positions['from_addr_hi']
            byte_pos_mid = self._parent.attribute_positions['from_addr_mid']
            byte_pos_low = self._parent.attribute_positions['from_addr_low']
            return BYTE_TO_HEX(bytes((self._parent.raw_msg[byte_pos_hi],
                                      self._parent.raw_msg[byte_pos_mid],
                                      self._parent.raw_msg[byte_pos_low],
                                      )))
        else:
            return False

    @property
    def device_ack(self):
        return self._device_ack

    @device_ack.setter
    def device_ack(self, boolean):
        self._device_ack = boolean
        if boolean == True:
            self._parent.device._add_to_hop_array(self.max_hops)
            self.device_success_callback()

    @property
    def device_success_callback(self):
        '''Function to run on successful device ack'''
        return self._device_success_callback

    @device_success_callback.setter
    def device_success_callback(self, value):
        self._device_success_callback = value
