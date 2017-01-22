import math
import time
import pprint

from .aldb import ALDB
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

    def query_aldb(self):
        self.clear_all_records()
        if self._parent.attribute('engine_version') == 0:
            self.i1_start_aldb_entry_query(0x0F, 0xF8)
        else:
            dev_bytes = {'msb': 0x00, 'lsb': 0x00}
            self._parent.send_command('read_aldb',
                                      'query_aldb',
                                      dev_bytes=dev_bytes)
            # It would be nice to link the trigger to the msb and lsb, but we
            # don't technically have that yet at this point
            trigger_attributes = {
                'plm_cmd': 0x51,
                'cmd_1': 0x2F,
                'from_addr_hi': self._parent.dev_addr_hi,
                'from_addr_mid': self._parent.dev_addr_mid,
                'from_addr_low': self._parent.dev_addr_low,
            }
            trigger = Trigger(trigger_attributes)
            trigger.trigger_function = lambda: self.i2_next_aldb()
            trigger_name = self._parent.dev_addr_str + 'query_aldb'
            self._parent.plm.trigger_mngr.add_trigger(trigger_name, trigger)

    def i2_next_aldb(self):
        # TODO parse by real names on incomming
        msb = self._parent.last_rcvd_msg.get_byte_by_name('usr_3')
        lsb = self._parent.last_rcvd_msg.get_byte_by_name('usr_4')
        if self.is_last_aldb(self.get_aldb_key(msb, lsb)):
            self._parent.remove_state_machine('query_aldb')
            records = self.get_all_records()
            for key in sorted(records):
                print(key, ":", BYTE_TO_HEX(records[key]))
            self._parent.send_command('light_status_request', 'set_aldb_delta')
        else:
            if lsb == 0x07:
                msb -= 1
                lsb = 0xFF
            else:
                lsb -= 8
            dev_bytes = {'msb': msb, 'lsb': lsb}
            self._parent.send_command('read_aldb',
                                      'query_aldb',
                                      dev_bytes=dev_bytes)
            # Set Trigger
            trigger_attributes = {
                'plm_cmd': 0x51,
                'cmd_1': 0x2F,
                'usr_3': msb,
                'usr_4': lsb,
                'from_addr_hi': self._parent.dev_addr_hi,
                'from_addr_mid': self._parent.dev_addr_mid,
                'from_addr_low': self._parent.dev_addr_low,
            }
            trigger = Trigger(trigger_attributes)
            trigger.trigger_function = lambda: self.i2_next_aldb()
            trigger_name = self._parent.dev_addr_str + 'query_aldb'
            self._parent.plm.trigger_mngr.add_trigger(trigger_name, trigger)

    def i1_start_aldb_entry_query(self, msb, lsb):
        message = self._parent.send_handler.create_message('set_address_msb')
        message.insert_bytes_into_raw({'msb': msb})
        message.insteon_msg.device_success_callback = \
            lambda: \
            self.peek_aldb(lsb)
        message.state_machine = 'query_aldb'
        self._parent._queue_device_msg(message)

    def peek_aldb(self, lsb):
        message = self._parent.send_handler.create_message('peek_one_byte')
        message.insert_bytes_into_raw({'lsb': lsb})
        message.state_machine = 'query_aldb'
        self._parent._queue_device_msg(message)

    def create_responder(self, controller, d1, d2, d3):
                # Device Responder
                # D1 On Level D2 Ramp Rate D3 Group of responding device i1 00
                # i2 01
        pass

    def create_controller(responder):
                # Device controller
                # D1 03 Hops?? D2 00 D3 Group 01 of responding device??
        pass

    def _write_link(self, linked_obj, is_controller):
        if self._parent.attribute('engine_version') == 2:
            pass  # run i2cs commands
        else:
            pass  # run i1 commands
        pass



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
            self.send_command('get_engine_version')
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
            trigger.trigger_function = lambda: self.send_command('light_status_request')
            self.plm.trigger_mngr.add_trigger(self.dev_addr_str + 'init_step_2', trigger)
            self.send_command('id_request')
        else:
            self.send_command('light_status_request')

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
        dev_cat = msg.get_byte_by_name('to_addr_hi')
        sub_cat = msg.get_byte_by_name('to_addr_mid')
        firmware = msg.get_byte_by_name('to_addr_low')
        self.set_dev_version(dev_cat,sub_cat,firmware)
        print('rcvd, broadcast updated devcat, subcat, and firmware')

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
            self.aldb.query_aldb()

    def set_engine_version(self, version):
        if version >= 0xFB:
            # Insteon Hack
            # Some I2CS Devices seem to have a bug in that they ack
            # a message when they mean to nack it, but the cmd_2
            # value is still the correct nack reason
            self.attribute('engine_version', 0x02)
            self._rcvd_handler.dispatch_direct_nack(msg)
        else:
            self.attribute('engine_version', version)
            # TODO handle this with a trigger?
            # Continue init step
            self._init_step_2()

    def get_last_rcvd_msg(self):
        return self._rcvd_handler.last_rcvd_msg

    ###################################################################
    ##
    # Outgoing Message Handling
    ##
    ###################################################################

    def send_command(self, command_name, state='', dev_bytes={}):
        message = self.send_handler.create_message(command_name)
        if message is not None:
            message.insert_bytes_into_raw(dev_bytes)
            message.state_machine = state
            self.queue_device_msg(message)

    def write_aldb_record(self, msb, lsb):
        # TODO This is only the base structure still need to add more basically
        # just deletes things right now
        dev_bytes = {'msb': msb, 'lsb': lsb}
        self.send_command('write_aldb', '', dev_bytes=dev_bytes)

    def add_plm_to_dev_link(self):
        # Put the PLM in Linking Mode
        # queues a message on the PLM
        message = self.plm.create_message('all_link_start')
        plm_bytes = {
            'link_code': 0x01,
            'group': 0x00,
        }
        message.insert_bytes_into_raw(plm_bytes)
        message.plm_success_callback = self._add_plm_to_dev_link_step2
        message.msg_failure_callback = self._add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self.plm.queue_device_msg(message)

    def _add_plm_to_dev_link_step2(self):
        # Put Device in linking mode
        message = self.send_handler.create_message('enter_link_mode')
        dev_bytes = {
            'cmd_2': 0x00
        }
        message.insert_bytes_into_raw(dev_bytes)
        message.insteon_msg.device_success_callback = (
            self._add_plm_to_dev_link_step3
        )
        message.msg_failure_callback = self._add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self.queue_device_msg(message)

    def _add_plm_to_dev_link_step3(self):
        trigger_attributes = {
            'from_addr_hi': self.dev_addr_hi,
            'from_addr_mid': self.dev_addr_mid,
            'from_addr_low': self.dev_addr_low,
            'link_code': 0x01,
            'plm_cmd': 0x53
        }
        trigger = Trigger(trigger_attributes)
        trigger.trigger_function = lambda: self._add_plm_to_dev_link_step4()
        self.plm.trigger_mngr.add_trigger(self.dev_addr_str + 'add_plm_step_3', trigger)
        print('device in linking mode')

    def _add_plm_to_dev_link_step4(self):
        print('plm->device link created')
        self.plm.remove_state_machine('link plm->device')
        self.remove_state_machine('link plm->device')
        # Next init step
        self._init_step_2()

    def _add_plm_to_dev_link_fail(self):
        print('Error, unable to create plm->device link')
        self.plm.remove_state_machine('link plm->device')
        self.remove_state_machine('link plm->device')
