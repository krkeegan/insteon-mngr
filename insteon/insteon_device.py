import math
import time
import pprint

from insteon.aldb import ALDB
from insteon.base_objects import Root_Insteon
from insteon.group import Insteon_Group
from insteon.plm_message import PLM_Message
from insteon.helpers import BYTE_TO_HEX
from insteon.trigger import Trigger
from insteon.devices.generic import GenericRcvdHandler, GenericSendHandler


class Device_ALDB(ALDB):

    def __init__(self, parent):
        super().__init__(parent)

    def get_aldb_key(self, msb, lsb):
        offset = 7 - (lsb % 8)
        highest_byte = lsb + offset
        key = bytes([msb, highest_byte])
        return BYTE_TO_HEX(key)

    def create_responder(self, controller, d1, d2, d3):
                # Device Responder
                # D1 On Level D2 Ramp Rate D3 Group of responding device i1 00
                # i2 01
        pass

    def create_controller(self, responder):
                # Device controller
                # D1 03 Hops?? D2 00 D3 Group 01 of responding device??
        pass

    def _write_link(self, linked_obj, is_controller):
        if self._parent.attribute('engine_version') == 2:
            pass  # run i2cs commands
        else:
            pass  # run i1 commands

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
        self.create_group(1, Insteon_Group)
        self._rcvd_handler = GenericRcvdHandler(self)
        self.send_handler = GenericSendHandler(self)
        self._init_step_1()

    def _init_step_1(self):
        if self.attribute('engine_version') is None:
            self.send_handler.get_engine_version()
        else:
            self._init_step_2()

    def _init_step_2(self):
        if (self.dev_cat is None or
                self.sub_cat is None or
                self.firmware is None):
            trigger_attributes = {
                'from_addr_hi': self.dev_addr_hi,
                'from_addr_mid': self.dev_addr_mid,
                'from_addr_low': self.dev_addr_low,
                'cmd_1': 0x01,
                'insteon_msg_type': 'broadcast'
            }
            trigger = Trigger(trigger_attributes)
            trigger.trigger_function = lambda: self.send_handler.get_status()
            trigger_name = self.dev_addr_str + 'init_step_2'
            self.plm.trigger_mngr.add_trigger(trigger_name, trigger)
            self.send_handler.get_device_version()
        else:
            self.send_handler.get_status()

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
            self._rcvd_handler.last_rcvd_msg = msg
            ret = self._dispatch_msg_rcvd(msg)

    def _dispatch_msg_rcvd(self, msg):
        '''Selects the proper message path based on the message type.'''
        if msg.insteon_msg.message_type == 'direct':
            self._process_direct_msg(msg)
        elif msg.insteon_msg.message_type == 'direct_ack':
            self._process_direct_ack(msg)
        elif msg.insteon_msg.message_type == 'direct_nack':
            self._process_direct_nack(msg)
        elif msg.insteon_msg.message_type == 'broadcast':
            self._process_broadcast(msg)
        elif msg.insteon_msg.message_type == 'alllink_cleanup_ack':
            self._process_alllink_cleanup(msg)

    def _process_direct_msg(self, msg):
        '''processes an incomming direct message'''
        processed = self._rcvd_handler.dispatch_direct(msg)
        if not processed:
            print('unhandled direct message, perhaps dev_cat is wrong')
            pprint.pprint(msg.__dict__)

    def _process_direct_ack(self, msg):
        '''processes an incomming direct ack message, sets the
        allow_tigger flags and device_acks flags'''
        if not self._is_valid_direct_resp(msg):
            msg.allow_trigger = False
        elif self._rcvd_handler.dispatch_direct_ack(msg) is False:
            msg.allow_trigger = False
        else:
            self.last_sent_msg.insteon_msg.device_ack = True

    def _process_direct_nack(self, msg):
        '''processes an incomming direct nack message'''
        if self._is_valid_direct_resp(msg):
            self._rcvd_handler.dispach_direct_nack(msg)

    def _process_broadcast(self,msg):
        self._rcvd_handler.dispatch_broadcast(msg)

    def _process_alllink_cleanup(self,msg):
        # TODO set state of the device based on cmd acked
        # Clear queued cleanup messages if they exist
        self._remove_cleanup_msgs(msg)
        if (self.last_sent_msg and
                self.last_sent_msg.get_byte_by_name('cmd_1') ==
                msg.get_byte_by_name('cmd_1') and
                self.last_sent_msg.get_byte_by_name('cmd_2') ==
                msg.get_byte_by_name('cmd_2')):
            # Only set ack if this was sent by this device
            self.last_sent_msg.insteon_msg.device_ack = True

    def _remove_cleanup_msgs(self, msg):
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

    def _is_valid_direct_resp(self, msg):
        ret = True
        if self.last_sent_msg.plm_ack is not True:
            print('ignoring a device response received before PLM ack')
            ret = False
        elif self.last_sent_msg.insteon_msg.device_ack is not False:
            print('ignoring an unexpected device response')
            ret = False
        elif (self.last_sent_msg.get_byte_by_name('cmd_1') !=
                msg.get_byte_by_name('cmd_1')):
            # This may be a status response STUPID INSTEON
            ret = False
            status = self._rcvd_handler.dispatch_status_resp(msg)
            if status is False:
                print('ignoring an unmatched response')
        return ret

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

    ###################################################################
    #
    # Device Attributes
    #
    ###################################################################

    def set_cached_state(self, state):
        self.attribute('status', state)

    def check_aldb_delta(self, aldb_delta):
        '''Checks and updates the cached aldb delta as necessary.  If device
        is in the correct state_machine, will update cache, otherwise will
        cause an ALDB rescan if the delta doesn't match the cache'''
        if self.state_machine == 'set_aldb_delta':
            # TODO, we want to change aldb_deltas that are at 0x00
            self.attribute('aldb_delta', aldb_delta)
            self.remove_state_machine('set_aldb_delta')
        elif self.attribute('aldb_delta') != aldb_delta:
            print('aldb has changed, rescanning')
            self.send_handler.query_aldb()

    def set_engine_version(self, version):
        if version >= 0xFB:
            # Insteon Hack
            # Some I2CS Devices seem to have a bug in that they ack
            # a message when they mean to nack it, but the cmd_2
            # value is still the correct nack reason
            self.attribute('engine_version', 0x02)
            self.send_handler.add_plm_to_dev_link()
        else:
            self.attribute('engine_version', version)
            # TODO handle this with a trigger?
            # Continue init step
            self._init_step_2()

    def get_last_rcvd_msg(self):
        return self._rcvd_handler.last_rcvd_msg
