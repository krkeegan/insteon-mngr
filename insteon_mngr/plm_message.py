import time
from insteon_mngr.plm_schema import PLM_SCHEMA
from insteon_mngr.insteon_message import Insteon_Message


class PLM_Message(object):
    # Initialization Functions

    def __init__(self, plm, **kwargs):
        self._plm = plm
        self._plm_ack = False
        self._time_plm_ack = 0
        self._extra_ack_time = 0
        self._plm_prelim_ack = False
        self._allow_trigger = True
        self._seq_time = 0
        self._seq_lock = False
        self._is_incomming = False
        self._plm_retry = 0
        self._failed = False
        self._plm_schema = {}
        self._raw_msg = bytes()
        self._insteon_msg = None
        self._insteon_attr = {}
        self._creation_time = time.time()
        self._time_sent = 0
        self._plm_success_callback = lambda: None
        self._msg_failed_callback = lambda: None
        if 'is_incomming' in kwargs:
            self._is_incomming = True
        self._device = None
        if 'device' in kwargs:
            self._device = kwargs['device']
        self.msg_from_raw(**kwargs)
        self.command_to_raw(**kwargs)

    @property
    def plm(self):
        return self._plm

    @property
    def device(self):
        return self._device

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def time_sent(self):
        return self._time_sent

    @time_sent.setter
    def time_sent(self, value):
        self._time_sent = value

    @property
    def time_plm_ack(self):
        return self._time_plm_ack

    @time_plm_ack.setter
    def time_plm_ack(self, value):
        self._time_plm_ack = value

    @property
    def extra_ack_time(self):
        return self._extra_ack_time

    @extra_ack_time.setter
    def extra_ack_time(self, value):
        self._extra_ack_time = value

    @property
    def time_due(self):
        return (self.time_sent + self.extra_ack_time)

    def msg_from_raw(self, **kwargs):
        if 'raw_data' not in kwargs:
            return
        self._plm_schema = PLM_SCHEMA[kwargs['raw_data'][1]].copy()
        self._raw_msg = kwargs['raw_data']
        self._init_insteon_msg(**kwargs)

    def command_to_raw(self, **kwargs):
        '''Takes a command dictionary and builds an Insteon
        message'''
        if 'plm_cmd' not in kwargs:
            return
        plm_cmd = kwargs['plm_cmd']
        plm_prefix = self._set_plm_schema(plm_cmd)
        if not plm_prefix:
            return
        if not self._initialize_raw_msg(plm_cmd, plm_prefix):
            return
        self._init_plm_msg(**kwargs)
        self._init_insteon_msg(**kwargs)
        return self

    def _init_plm_msg(self, **kwargs):
        if 'plm_bytes' in kwargs:
            plm_bytes = kwargs['plm_bytes']
            for key in plm_bytes:
                if key in self.attribute_positions:
                    self._insert_byte_into_raw(plm_bytes[key], key)

    def _init_insteon_msg(self, **kwargs):
        if self.plm_schema['name'] in ['insteon_received',
                                       'insteon_ext_received', 'insteon_send']:
            self._insteon_msg = Insteon_Message(self, **kwargs)

    def _initialize_raw_msg(self, plm_cmd, plm_prefix):
        msg_direction = 'send_len'
        if self.is_incomming:
            msg_direction = 'rcvd_len'
        if msg_direction in self.plm_schema:
            self._msg_byte_length = self.plm_schema[msg_direction]
            self._raw_msg = bytearray(self.plm_schema[msg_direction][0])
            self._raw_msg[0] = 0x02
            self._raw_msg[1] = plm_prefix
            return True
        else:
            return False

    # Set Bytes in Message
    def _set_plm_schema(self, plm_cmd):
        plm_schema = False
        for plm_prefix, schema in PLM_SCHEMA.items():
            if schema['name'] == plm_cmd:
                plm_schema = schema
                break
        if plm_schema:
            self._plm_schema = plm_schema
            return plm_prefix
        else:
            print("I don't know that plm command")
            return False

    def _insert_byte_into_raw(self, data_byte, pos_name):
        if pos_name in self.attribute_positions:
            pos = self.attribute_positions[pos_name]
            self._raw_msg[pos] = data_byte
        return

    def insert_bytes_into_raw(self, byte_dict):
        for name, byte in byte_dict.items():
            self._insert_byte_into_raw(byte, name)
        return

    # Read Message Bytes
    @property
    def attribute_positions(self):
        msg_direction = 'send_byte_pos'
        if self.is_incomming:
            msg_direction = 'recv_byte_pos'
        ret = self._insteon_attr.copy()
        ret.update(self.plm_schema[msg_direction])
        return ret

    @property
    def parsed_attributes(self):
        '''Returns a dictionary of the attribute names associated with their
        byte values'''
        ret = {}
        for name in self.attribute_positions.keys():
            ret[name] = self.get_byte_by_name(name)
        return ret

    @property
    def plm_resp_flag(self):
        if 'plm_resp' in self.attribute_positions or \
                'plm_resp_e' in self.attribute_positions:
            byte_pos = self.attribute_positions['plm_resp']
            if 'plm_resp_e' in self.attribute_positions:
                byte_pos_e = self.attribute_positions['plm_resp_e']
                if byte_pos_e < len(self.raw_msg):
                    byte_pos = byte_pos_e
            return self.raw_msg[byte_pos]
        else:
            return False

    @property
    def plm_resp_ack(self):
        ret = False
        if self.plm_resp_flag == 0x06:
            ret = True
        return ret

    @property
    def plm_resp_nack(self):
        ret = False
        if self.plm_resp_flag == 0x15:
            ret = True
        return ret

    @property
    def plm_resp_bad_cmd(self):
        ret = False
        if self.plm_resp_flag == 0x0F:
            ret = True
        return ret

    @property
    def raw_msg(self):
        return self._raw_msg.copy()

    def get_byte_by_name(self, byte_name):
        ret = False
        if byte_name in self.attribute_positions:
            pos = self.attribute_positions[byte_name]
            if pos < len(self.raw_msg):
                ret = self.raw_msg[pos]
        return ret

    # Message Meta Data
    @property
    def plm_schema(self):
        return self._plm_schema.copy()

    @property
    def plm_cmd_type(self):
        return self.plm_schema['name']

    @property
    def is_incomming(self):
        return self._is_incomming

    @property
    def failed(self):
        return self._failed

    @failed.setter
    def failed(self, boolean):
        self._failed = boolean
        if boolean is True:
            self._msg_failed_callback()

    @property
    def plm_ack(self):
        return self._plm_ack

    @plm_ack.setter
    def plm_ack(self, boolean):
        self._plm_ack = boolean
        if boolean is True:
            self.plm_success_callback()

    @property
    def plm_prelim_ack(self):
        return self._plm_prelim_ack

    @plm_prelim_ack.setter
    def plm_prelim_ack(self, boolean):
        self._plm_prelim_ack = boolean

    @property
    def allow_trigger(self):
        return self._allow_trigger

    @allow_trigger.setter
    def allow_trigger(self, boolean):
        self._allow_trigger = boolean

    @property
    def plm_retry(self):
        return self._plm_retry

    @plm_retry.setter
    def plm_retry(self, count):
        self._plm_retry = count

    @property
    def insteon_msg(self):
        return self._insteon_msg

    @property
    def seq_lock(self):
        return self._seq_lock

    @seq_lock.setter
    def seq_lock(self, boolean):
        self._seq_lock = boolean

    @property
    def seq_time(self):
        return self._seq_time

    @seq_time.setter
    def seq_time(self, int_parm):
        self._seq_time = int_parm

    @property
    def plm_success_callback(self):
        '''Function to run on successful plm ack'''
        return self._plm_success_callback

    @plm_success_callback.setter
    def plm_success_callback(self, value):
        self._plm_success_callback = value

    @property
    def msg_failure_callback(self):
        '''Function to run on failure of message.  Could be either a
        PLM or Device Nack or failure'''
        return self._msg_failed_callback

    @msg_failure_callback.setter
    def msg_failure_callback(self, value):
        self._msg_failed_callback = value
