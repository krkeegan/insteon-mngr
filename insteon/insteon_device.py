import math
import time

from insteon.aldb import ALDB
from insteon.base_objects import Root_Insteon, BYTE_TO_HEX
from insteon.group import Insteon_Group
from insteon.devices import (GenericRcvdHandler, GenericSendHandler,
    GenericFunctions, select_device, select_group)


class Device_ALDB(ALDB):

    def __init__(self, parent):
        super().__init__(parent)

    def get_aldb_key(self, msb, lsb):
        offset = 7 - (lsb % 8)
        highest_byte = lsb + offset
        key = bytes([msb, highest_byte])
        return BYTE_TO_HEX(key)

    def get_next_aldb_address(self, msb, lsb):
        ret = {}
        if (self._parent.attribute('engine_version') == 0x00):
            ret['msb'] = msb
            if self.is_empty_aldb(self.get_aldb_key(msb, lsb)):
                ret['lsb'] = lsb - (8 + (lsb % 8))
            elif (lsb % 8) == 7: # End of Entry
                ret['lsb'] = lsb - 15
            else: # In an entry, keep counting up
                ret['lsb'] = lsb + 1
            if ret['lsb'] < 0: #Bottom of LSB start over
                ret['msb'] = msb - 1
                ret['lsb'] = 0xF8
        else:
            # TODO the i2 version is not very robust, it would explode if
            # it was sent anything other than the starting byte of an address
            if lsb == 0x07:
                msb -= 1
                lsb = 0xFF
            else:
                lsb -= 8
            ret['msb'] = msb
            ret['lsb'] = lsb
        return ret

    def store_peeked_byte(self, msb, lsb, byte):
        if (lsb % 8) == 0:
            # First byte, clear out the record
            self.edit_record(self.get_aldb_key(msb, lsb), bytearray(8))
        self.edit_record_byte(
            self.get_aldb_key(msb, lsb),
            lsb % 8,
            byte
        )

class InsteonDevice(Root_Insteon):

    def __init__(self, core, plm, **kwargs):
        self.aldb = Device_ALDB(self)
        super().__init__(core, plm, **kwargs)
        # TODO move this to command handler?
        self.last_sent_msg = None
        self._recent_inc_msgs = {}
        self._rcvd_handler = GenericRcvdHandler(self)
        self.send_handler = GenericSendHandler(self)
        self.functions = GenericFunctions(self)
        self.send_handler.initialize_device()

    @property
    def smart_hops(self):
        if self.attribute('hop_array') is not None:
            avg = (
                sum(self.attribute('hop_array')) /
                float(len(self.attribute('hop_array')))
            )
        else:
            avg = 3
        return math.ceil(avg)

    @property
    def engine_version(self):
        return self.attribute('engine_version')

    ###################################################################
    ##
    # Incoming Message Handling
    ##
    ###################################################################

    def msg_rcvd(self, msg):
        '''Checks to see if the incomming message is valid, extracts
        hop and plm wait time data, passes valid messages onto the
        dispatcher'''
        ret = None
        self._set_plm_wait(msg)
        if self._is_duplicate(msg):
            msg.allow_trigger = False
            print('Skipped duplicate msg')
            ret = None
        else:
            self._process_hops(msg)
            ret = self._rcvd_handler.dispatch_msg_rcvd(msg)

    def _process_hops(self, msg):
        if (msg.insteon_msg.message_type == 'direct' or
                msg.insteon_msg.message_type == 'direct_ack' or
                msg.insteon_msg.message_type == 'direct_nack'):
            hops_used = msg.insteon_msg.max_hops - msg.insteon_msg.hops_left
            hop_array = self.attribute('hop_array')
            if hop_array is None:
                hop_array = []
            hop_array.append(hops_used)
            extra_data = len(hop_array) - 10
            if extra_data > 0:
                hop_array = hop_array[extra_data:]
            self.attribute('hop_array', hop_array)

    def _set_plm_wait(self, msg):
        # Wait for additional hops to arrive
        hop_delay = 50 if msg.insteon_msg.msg_length == 'standard' else 109
        total_delay = hop_delay * msg.insteon_msg.hops_left
        expire_time = (total_delay / 1000)
        # Force a 5 millisecond delay for all
        self.plm.wait_to_send = expire_time + (5 / 1000)

    def _is_duplicate(self, msg):
        '''Checks to see if this is a duplicate message'''
        ret = None
        self._clear_stale_dupes()
        if self._is_msg_in_recent(msg):
            ret = True
        else:
            self._store_msg_in_recent(msg)
            ret = False
        return ret

    def _clear_stale_dupes(self):
        current_time = time.time()
        msgs_to_delete = []
        for msg, wait_time in self._recent_inc_msgs.items():
            if wait_time < current_time:
                msgs_to_delete.append(msg)
        for msg in msgs_to_delete:
            del self._recent_inc_msgs[msg]

    def _get_search_key(self, msg):
        # Zero out max_hops and hops_left
        # arguable whether this should be done in the Insteon_Message class
        search_bytes = msg.raw_msg
        search_bytes[8] = search_bytes[8] & 0b11110000
        return BYTE_TO_HEX(search_bytes)

    def _is_msg_in_recent(self, msg):
        search_key = self._get_search_key(msg)
        if search_key in self._recent_inc_msgs:
            return True

    def _store_msg_in_recent(self, msg):
        search_key = self._get_search_key(msg)
        # These numbers come from real world use
        hop_delay = 87 if msg.insteon_msg.msg_length == 'standard' else 183
        total_delay = hop_delay * msg.insteon_msg.hops_left
        expire_time = time.time() + (total_delay / 1000)
        self._recent_inc_msgs[search_key] = expire_time

    def remove_cleanup_msgs(self, msg):
        cmd_1 = msg.get_byte_by_name('cmd_1')
        cmd_2 = msg.get_byte_by_name('cmd_2')
        for state, msgs in self._device_msg_queue.items():
            i = 0
            to_delete = []
            for msg in msgs:
                if msg.get_byte_by_name('cmd_1') == cmd_1 and \
                        msg.get_byte_by_name('cmd_2') == cmd_2:
                    to_delete.append(i)
                i += 1
            for position in reversed(to_delete):
                del self._device_msg_queue[state][position]

    ###################################################################
    #
    # Device Attributes
    #
    ###################################################################

    def set_cached_state(self, state):
        self.attribute('status', state)

    def set_aldb_delta(self, delta):
        self.attribute('aldb_delta', delta)

    def set_engine_version(self, version):
        if version >= 0xFB:
            # Insteon Hack
            # Some I2CS Devices seem to have a bug in that they ack
            # a message when they mean to nack it, but the cmd_2
            # value is still the correct nack reason
            self.attribute('engine_version', 0x02)
            self.send_handler.add_plm_to_dev_link()
        else:
            # requesting an engine version will always cause a status request
            # this is more likely an error in the init_sequence than anything
            # else
            self.attribute('engine_version', version)
            self.send_handler.initialize_device()

    def get_last_rcvd_msg(self):
        return self._rcvd_handler.last_rcvd_msg

    def get_responder_data1(self):
        return self.functions.get_responder_data1()

    def get_responder_data2(self):
        return self.functions.get_responder_data2()

    def get_responder_data3(self):
        return self.functions.get_responder_data3()

    def update_device_classes(self):
        classes = select_device(device=self, dev_cat=self.dev_cat,
                                sub_cat=self.sub_cat, firmware=self.firmware,
                                engine_version=self.engine_version)
        self._rcvd_handler = classes['rcvd_handler']
        self.send_handler = classes['send_handler']
        self.functions = classes['functions']
        for group in self.get_all_groups():
            classes = select_group(device=group, dev_cat=group.dev_cat,
                                    sub_cat=group.sub_cat,
                                    firmware=group.firmware,
                                    engine_version=group.engine_version)
            group.send_handler = classes['send_handler']
            group.functions = classes['functions']
