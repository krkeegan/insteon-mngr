import time
import datetime

from insteon.insteon_device import InsteonDevice
from insteon.base_objects import Root_Insteon
from insteon.aldb import ALDB
from insteon.trigger import Trigger_Manager, PLMTrigger
from insteon.plm_message import PLM_Message
from insteon.helpers import BYTE_TO_HEX, BYTE_TO_ID, HOUSE_TO_BYTE, UNIT_TO_BYTE
from insteon.plm_schema import PLM_SCHEMA
from insteon.x10_device import X10_Device
from insteon.group import PLM_Group


class Modem_ALDB(ALDB):

    def add_record(self, aldb):
        position = str(len(self.aldb) + 1)
        position = position.zfill(4)
        self.aldb[position] = aldb
        parsed_record = self.parse_record(position)
        # TODO if this is a PLM controller record, we may also know the
        # dev_cat sub_cat and firmware of this device, although they may
        # not be accurate.  Should we do something with this just in case
        # we are unable to reach the device such as motion sensors, remotes...
        self._parent.add_device(BYTE_TO_ID(parsed_record['dev_addr_hi'],
                                parsed_record['dev_addr_mid'],
                                parsed_record['dev_addr_low']))

    def have_aldb_cache(self):
        # TODO This will return false for an empty aldb as well, do we care?
        ret = True
        if len(self.aldb) == 0:
            ret = False
        return ret

    def query_aldb(self):
        '''Queries the PLM for a list of the link records saved on
        the PLM and stores them in the cache'''
        self.clear_all_records()
        self._parent.send_command('all_link_first_rec', 'query_aldb')

    def create_responder(self, controller, *args):
        self._write_link(controller, is_plm_controller=False)

    def create_controller(self, controller, *args):
        self._write_link(controller, is_plm_controller=True)

    def _write_link(self, linked_obj, is_plm_controller):
        group = linked_obj.group_number
        if is_plm_controller:
            group = self._parent.group_number
        link_bytes = {
            'controller': True if is_plm_controller else False,
            'responder': False if is_plm_controller else True,
            'group': group,
            'dev_addr_hi': linked_obj.dev_addr_hi,
            'dev_addr_mid': linked_obj.dev_addr_mid,
            'dev_addr_low': linked_obj.dev_addr_low,
        }
        del link_bytes['controller']
        del link_bytes['responder']
        records = self.get_matching_records(link_bytes)
        link_flags = 0xE2 if is_plm_controller else 0xA2
        ctrl_code = 0x20
        if (len(records) == 0):
            ctrl_code = 0x40 if is_plm_controller else 0x41
        link_bytes.update({
            'ctrl_code': ctrl_code,
            'link_flags': link_flags,
            'data_1': linked_obj.dev_cat,
            'data_2': linked_obj.sub_cat,
            'data_3': linked_obj.firmware
        })
        self._parent.send_command('all_link_manage_rec', '', link_bytes)



class Modem(Root_Insteon):

    def __init__(self, core, **kwargs):
        self._devices = {}
        self.aldb = Modem_ALDB(self)
        self.trigger_mngr = Trigger_Manager(self)
        super().__init__(core, self, **kwargs)
        self._read_buffer = bytearray()
        self._last_sent_msg = None
        self._msg_queue = []
        self._wait_to_send = 0
        self._last_x10_house = None
        self._last_x10_unit = None
        self.port_active = True
        self.ack_time = 75
        for group_num in range(0x01, 0xFF):
            self.create_group(group_num, PLM_Group)

    def _load_devices(self, devices):
        for id, attributes in devices.items():
            self.add_device(id, attributes=attributes)

    def setup(self):
        if self.dev_addr_str == '000000':
            self.send_command('plm_info')
        if self.aldb.have_aldb_cache() is False:
            self.aldb.query_aldb()

    def set_ack_time(self,milliseconds):
        self.ack_time = milliseconds
        return

    @property
    def type(self):
        return self.attribute('type')

    def add_device(self, device_id, **kwargs):
        device_id = device_id.upper()
        if device_id not in self._devices:
            self._devices[device_id] = InsteonDevice(self.core,
                                                      self,
                                                      device_id=device_id,
                                                      **kwargs)
        return self._devices[device_id]

    def add_x10_device(self, address):
        # We convert the address to its 'byte' value immediately
        # TODO, this is bad, the insteon devices are stored by a hex str
        byte_address = (
            HOUSE_TO_BYTE[address[0:1].lower()] | UNIT_TO_BYTE[address[1:2]])
        self._devices[byte_address] = X10_Device(self.core,
                                                 self,
                                                 byte_address=byte_address)
        return self._devices[byte_address]

    def process_input(self):
        '''Reads available bytes from PLM, then parses the bytes
            into a message'''
        self._read()
        self._advance_to_msg_start()
        bytes = self._parse_read_buffer()
        if bytes:
            self.process_inc_msg(bytes)

    def _advance_to_msg_start(self):
        '''Removes extraneous bytes from start of read buffer'''
        if len(self._read_buffer) >= 2:
            # Handle Errors First
            good_prefix = bytes.fromhex('02')
            wait_prefix = bytes.fromhex('15')
            if not self._read_buffer.startswith((good_prefix, wait_prefix)):
                print('Removed bad starting string from', BYTE_TO_HEX(
                    self._read_buffer))
                index = self._read_buffer.find(good_prefix)
                del self._read_buffer[0:index]
                print('resulting buffer is', BYTE_TO_HEX(self._read_buffer))
            if self._read_buffer.startswith(wait_prefix):
                print('need to slow down!!', BYTE_TO_HEX(self._read_buffer))
                self.wait_to_send = .5
                del self._read_buffer[0:1]
                self._advance_to_msg_start()

    def _parse_read_buffer(self):
        '''Parses messages out of the read buffer'''
        ret = None
        if len(self._read_buffer) >= 2:
            # Process the message
            cmd_prefix = self._read_buffer[1]
            if cmd_prefix in PLM_SCHEMA:
                byte_length = PLM_SCHEMA[cmd_prefix]['rcvd_len']
                # This solves Insteon stupidity.  0x62 messages can
                # be either standard or extended length.  The only way
                # to determine which length we have received is to look
                # at the message flags
                is_extended = 0
                if (cmd_prefix == 0x62 and
                        len(self._read_buffer) >= 6 and
                        self._read_buffer[5] & 16):
                    is_extended = 1
                msg_length = byte_length[is_extended]
                if msg_length <= len(self._read_buffer):
                    ret = self._read_buffer[0:msg_length]
                    del self._read_buffer[0:msg_length]
            else:
                print("error, I don't know this prefix",
                      format(cmd_prefix, 'x'))
                index = self._read_buffer.find(bytes.fromhex('02'))
                del self._read_buffer[0:index]
        return ret

    @property
    def wait_to_send(self):
        return self._wait_to_send

    @wait_to_send.setter
    def wait_to_send(self, value):
        if self._wait_to_send < time.time():
            self._wait_to_send = time.time()
        self._wait_to_send += value

    def process_inc_msg(self, raw_msg):
        now = datetime.datetime.now().strftime("%M:%S.%f")
        print(now, 'found legitimate msg', BYTE_TO_HEX(raw_msg))
        msg = PLM_Message(self, raw_data=raw_msg, is_incomming=True)
        self._msg_dispatcher(msg)
        self.trigger_mngr.test_triggers(msg)
        # TODO clean up expired triggers?

    def _msg_dispatcher(self, msg):
        if msg.plm_resp_ack:
            if 'ack_act' in msg.plm_schema:
                msg.plm_schema['ack_act'](self, msg)
            else:
                # Attempting default action
                self.rcvd_plm_ack(msg)
        elif msg.plm_resp_nack:
            self.wait_to_send = .5
            if 'nack_act' in msg.plm_schema:
                msg.plm_schema['nack_act'](self, msg)
            else:
                print('PLM sent NACK to last command, retrying last message')
        elif msg.plm_resp_bad_cmd:
            self.wait_to_send = .5
            if 'bad_cmd_act' in msg.plm_schema:
                msg.plm_schema['bad_cmd_act'](self, msg)
            else:
                print('PLM said bad command, retrying last message')
        elif 'recv_act' in msg.plm_schema:
            msg.plm_schema['recv_act'](self, msg)

    def get_device_by_addr(self, addr):
        ret = None
        try:
            ret = self._devices[addr]
        except KeyError:
            print('error, unknown device address=', addr)
        return ret

    def get_all_devices(self):
        ret = []
        for addr, device in self._devices.items():
            ret.append(device)
        return ret

    def _send_msg(self, msg):
        self._last_sent_msg = msg
        self.write(msg)

    def _resend_failed_msg(self):
        msg = self._last_sent_msg
        msg.plm_ack = False
        msg.plm_prelim_ack = False
        if msg._insteon_msg:
            msg._insteon_msg.hops_left += 1
            msg._insteon_msg.max_hops += 1
            msg._insteon_msg.device_prelim_ack = False
        self._last_sent_msg = {}
        if msg._device:
            msg._device._resend_msg(msg)
        else:
            self._resend_msg(msg)

    def write(self, msg):
        now = datetime.datetime.now().strftime("%M:%S.%f")
        if msg.insteon_msg:
            msg.insteon_msg._set_i2cs_checksum()
        if self.port_active:
            print(now, 'sending data', BYTE_TO_HEX(msg.raw_msg))
            msg.time_sent = time.time()
            self._write(msg.raw_msg)
        else:
            msg.failed = True
            port = None
            if self.type == 'plm':
                port = self.port
            elif self.type =='hub':
                port = self.tcp_port
            print(
                now,
                'Error: the modem on port',
                port,
                'is not active, unable to send message'
            )
        return

    def plm_info(self, msg_obj):
        if (self._last_sent_msg.plm_cmd_type == 'plm_info' and
                msg_obj.plm_resp_ack):
            self._last_sent_msg.plm_ack = True
            dev_addr_hi = msg_obj.get_byte_by_name('plm_addr_hi')
            dev_addr_mid = msg_obj.get_byte_by_name('plm_addr_mid')
            dev_addr_low = msg_obj.get_byte_by_name('plm_addr_low')
            self.set_dev_addr(BYTE_TO_ID(dev_addr_hi,
                                         dev_addr_mid,
                                         dev_addr_low))
            dev_cat = msg_obj.get_byte_by_name('dev_cat')
            sub_cat = msg_obj.get_byte_by_name('sub_cat')
            firmware = msg_obj.get_byte_by_name('firmware')
            self.set_dev_version(dev_cat,sub_cat,firmware)


    def send_command(self, command, state='', plm_bytes={}):
        message = self.create_message(command)
        message.insert_bytes_into_raw(plm_bytes)
        message.state_machine = state
        self.queue_device_msg(message)

    def create_message(self, command):
        message = PLM_Message(
            self, device=self,
            plm_cmd=command)
        return message

    def process_unacked_msg(self):
        '''checks for unacked messages'''
        if self._is_ack_pending():
            msg = self._last_sent_msg
        else:
            return
        now = datetime.datetime.now().strftime("%M:%S.%f")
        # allow 75 milliseconds for the PLM to ack a message
        if msg.plm_ack is False:
            if msg.time_sent < time.time() - (self.ack_time / 1000):
                print(now, 'PLM failed to ack the last message')
                if msg.plm_retry >= 3:
                    print(now, 'PLM retries exceeded, abandoning this message')
                    msg.failed = True
                else:
                    msg.plm_retry += 1
                    self._resend_failed_msg()
            return
        if msg.seq_lock:
            if msg.time_sent < time.time() - msg.seq_time:
                print(now, 'PLM sequence lock expired, moving on')
                msg.seq_lock = False
            return
        if msg.insteon_msg and msg.insteon_msg.device_ack is False:
            total_hops = msg.insteon_msg.max_hops * 2
            hop_delay = 75 if msg.insteon_msg.msg_length == 'standard' else 200
            # Increase delay on each subsequent retry
            hop_delay = (msg.insteon_msg.device_retry + 1) * hop_delay
            # Add 1 additional second based on trial and error, perhaps
            # to allow device to 'think'
            total_delay = (total_hops * hop_delay / 1000) + 1
            if msg.time_plm_ack < time.time() - total_delay:
                print(
                    now,
                    'device failed to ack a message, total delay =',
                    total_delay, 'total hops=', total_hops)
                if msg.insteon_msg.device_retry >= 3:
                    print(
                        now,
                        'device retries exceeded, abandoning this message')
                    msg.failed = True
                else:
                    msg.insteon_msg.device_retry += 1
                    self._resend_failed_msg()
            return

    def process_queue(self):
        '''Determines and sends the next message.
        Preferentially sends a message from the same device with the same
        state_machine as the perviously sent message.
        Otherwise, loops through all of the devices and sends the
        oldest message currently waiting in a device queue
        if there are no other conflicts'''
        if (not self._is_ack_pending() and
                time.time() > self.wait_to_send):
            last_device = None
            last_state = None
            next_state = None
            send_msg = None
            if self._last_sent_msg:
                last_device = self._last_sent_msg.device
                last_state = self._last_sent_msg.state_machine
                next_state = last_device._get_next_state_machine()
            if (last_device is not None and
                    last_device.next_msg_create_time() is not None):
                send_msg = last_device.pop_device_queue()
            else:
                devices = [self, ]
                msg_time = 0
                sending_device = False
                for id, device in self._devices.items():
                    devices.append(device)
                for device in devices:
                    dev_msg_time = device.next_msg_create_time()
                    if dev_msg_time and (msg_time == 0 or
                                         dev_msg_time < msg_time):
                        sending_device = device
                        msg_time = dev_msg_time
                if sending_device:
                    send_msg = sending_device.pop_device_queue()
            if send_msg:
                if send_msg.insteon_msg:
                    device = send_msg.device
                    device.last_sent_msg = send_msg
                self._send_msg(send_msg)

    def _is_ack_pending(self):
        ret = False
        if self._last_sent_msg and not self._last_sent_msg.failed:
            if self._last_sent_msg.seq_lock:
                ret = True
            elif not self._last_sent_msg.plm_ack:
                ret = True
            elif (self._last_sent_msg.insteon_msg and
                    not self._last_sent_msg.insteon_msg.device_ack):
                ret = True
        return ret

    def rcvd_plm_ack(self, msg):
        if (self._last_sent_msg.plm_ack is False and
                msg.raw_msg[0:-1] == self._last_sent_msg.raw_msg):
            self._last_sent_msg.plm_ack = True
            self._last_sent_msg.time_plm_ack = time.time()
        else:
            msg.allow_trigger = False
            print('received spurious plm ack')

    def rcvd_prelim_plm_ack(self, msg):
        # TODO consider some way to increase allowable ack time
        if (self._last_sent_msg.plm_prelim_ack is False and
                self._last_sent_msg.plm_ack is False and
                msg.raw_msg[0:-1] == self._last_sent_msg.raw_msg):
            self._last_sent_msg.plm_prelim_ack = True
        else:
            msg.allow_trigger = False
            print('received spurious prelim plm ack')

    def rcvd_all_link_manage_ack(self, msg):
        aldb = msg.raw_msg[3:11]
        ctrl_code = msg.get_byte_by_name('ctrl_code')
        link_flags = msg.get_byte_by_name('link_flags')
        search_attributes = {
            'controller': True if link_flags & 0b01000000 else False,
            'responder': True if ~link_flags & 0b01000000 else False,
            'group': msg.get_byte_by_name('group'),
            'dev_addr_hi': msg.get_byte_by_name('dev_addr_hi'),
            'dev_addr_mid': msg.get_byte_by_name('dev_addr_mid'),
            'dev_addr_low': msg.get_byte_by_name('dev_addr_low'),
        }
        if ctrl_code == 0x40 or ctrl_code == 0x41:
            self.aldb.add_record(aldb)
        elif ctrl_code == 0x20:
            records = self.aldb.get_matching_records(search_attributes)
            try:
                self.aldb.edit_record(records[0], aldb)
            except:
                print('error trying to edit plm aldb cache')
        elif ctrl_code == 0x80:
            records = self.aldb.get_matching_records(search_attributes)
            try:
                self.aldb.delete_record(records[0], aldb)
            except:
                print('error trying to delete plm aldb cache')
        self.rcvd_plm_ack(msg)

    def rcvd_all_link_manage_nack(self, msg):
        print('error writing aldb to PLM, will rescan plm and try again')
        plm = self
        self._last_sent_msg.failed = True
        self.aldb.query_aldb()
        trigger_attributes = {
            'plm_cmd': 0x6A,
            'plm_resp': 0x15
        }
        trigger = PLMTrigger(plm=self, attributes=trigger_attributes)
        dev_addr_hi = msg.get_byte_by_name('dev_addr_hi')
        dev_addr_mid = msg.get_byte_by_name('dev_addr_mid')
        dev_addr_low = msg.get_byte_by_name('dev_addr_low')
        device_id = BYTE_TO_ID(dev_addr_hi, dev_addr_mid, dev_addr_low)
        device = self.get_device_by_addr(device_id)
        is_controller = False
        if msg.get_byte_by_name('link_flags') == 0xE2:
            plm = self.get_object_by_group_num(msg.get_byte_by_name('group'))
            is_controller = True
        else:
            device = device.get_object_by_group_num(
                msg.get_byte_by_name('group'))
        trigger.trigger_function = lambda: plm.aldb._write_link(
            device, is_controller)
        trigger.name = 'rcvd_all_link_manage_nack'
        trigger.queue()

    def rcvd_insteon_msg(self, msg):
        insteon_obj = self.get_device_by_addr(msg.insteon_msg.from_addr_str)
        if insteon_obj is not None:
            insteon_obj.msg_rcvd(msg)

    def rcvd_plm_x10_ack(self, msg):
        # For some reason we have to slow down when sending X10 msgs to the PLM
        self.rcvd_plm_ack(msg)
        self.wait_to_send = .5

    def rcvd_aldb_record(self, msg):
        if (self._last_sent_msg.plm_ack is False and
                self._last_sent_msg.plm_prelim_ack is True):
            self._last_sent_msg.plm_ack = True
            self._last_sent_msg.time_plm_ack = time.time()
            self.aldb.add_record(msg.raw_msg[2:])
            self.send_command('all_link_next_rec', 'query_aldb')
        else:
            msg.allow_trigger = False
            print('received spurious plm aldb record')

    def end_of_aldb(self, msg):
        self._last_sent_msg.plm_ack = True
        self.remove_state_machine('query_aldb')
        print('reached the end of the PLMs ALDB')
        records = self.aldb.get_all_records()
        for key in sorted(records):
            print(key, ":", BYTE_TO_HEX(records[key]))

    def rcvd_all_link_complete(self, msg):
        if msg.get_byte_by_name('link_code') == 0xFF:
            # DELETE THINGS
            pass
        else:
            # Fix stupid discrepancy in Insteon spec
            link_flag = 0xA2
            if msg.get_byte_by_name('link_code') == 0x01:
                link_flag = 0xE2
            record = bytearray(8)
            record[0] = link_flag
            record[1:8] = msg.raw_msg[3:]
            self.aldb.add_record(record)
            # notify the linked device
            device_id = BYTE_TO_ID(record[2], record[3], record[4])
            device = self.get_device_by_addr(device_id)
            if msg.get_byte_by_name('link_code') == 0x01:
                dev_cat = msg.get_byte_by_name('dev_cat')
                sub_cat = msg.get_byte_by_name('sub_cat')
                firmware = msg.get_byte_by_name('firmware')
                device.set_dev_version(dev_cat, sub_cat, firmware)

    def rcvd_btn_event(self, msg):
        print("The PLM Button was pressed")
        # Currently there is no processing of this event

    def rcvd_plm_reset(self, msg):
        self.aldb.clear_all_records()
        print("The PLM was manually reset")

    def rcvd_x10(self, msg):
        if msg.get_byte_by_name('x10_flags') == 0x00:
            self.store_x10_address(msg.get_byte_by_name('raw_x10'))
        else:
            self._dispatch_x10_cmd(msg)

    def store_x10_address(self, byte):
        self._last_x10_house = byte & 0b11110000
        self._last_x10_unit = byte & 0b00001111

    def get_x10_address(self):
        return self._last_x10_house | self._last_x10_unit

    def _dispatch_x10_cmd(self, msg):
        if (self._last_x10_house ==
                msg.get_byte_by_name('raw_x10') & 0b11110000):
            try:
                device = self._devices[self.get_x10_address()]
                device.inc_x10_msg(msg)
            except KeyError:
                print('Received and X10 command for an unknown device')
        else:
            msg.allow_trigger = False
            print("X10 Command House Code did not match expected House Code")
            print("Message ignored")

    def rcvd_all_link_clean_status(self, msg):
        if self._last_sent_msg.plm_cmd_type == 'all_link_send':
            self._last_sent_msg.seq_lock = False
            if msg.plm_resp_ack:
                print('Send All Link - Success')
                self.remove_state_machine('all_link_send')
                # TODO do we update the device state here? or rely on arrival
                # of alllink_cleanup acks?  As it stands, our own alllink
                # cleanups will be sent if this msg is rcvd, but no official
                # device alllink cleanup arrives
            elif msg.plm_resp_nack:
                print('Send All Link - Error')
                # We don't resend, instead we rely on individual device
                # alllink cleanups to do the work
                self.remove_state_machine('all_link_send')
        else:
            msg.allow_trigger = False
            print('Ignored spurious all link clean status')

    def rcvd_all_link_clean_failed(self, msg):
        failed_addr = bytearray()
        failed_addr.extend(msg.get_byte_by_name('fail_addr_hi'))
        failed_addr.extend(msg.get_byte_by_name('fail_addr_mid'))
        failed_addr.extend(msg.get_byte_by_name('fail_addr_low'))
        print('A specific device faileled to ack the cleanup msg from addr',
              BYTE_TO_HEX(failed_addr))

    def rcvd_all_link_start(self, msg):
        if msg.plm_resp_ack:
            self._last_sent_msg.plm_ack = True
