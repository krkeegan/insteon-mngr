import time
import datetime

from insteon_mngr import BYTE_TO_HEX, BYTE_TO_ID
from insteon_mngr.insteon_device import InsteonDevice
from insteon_mngr.base_objects import Root, Group
from insteon_mngr.aldb import ALDB
from insteon_mngr.trigger import Trigger_Manager
from insteon_mngr.plm_message import PLM_Message
from insteon_mngr.plm_schema import PLM_SCHEMA
from insteon_mngr.devices import ModemSendHandler
from insteon_mngr.modem_rcvd import ModemRcvdHandler
from insteon_mngr.sequences import WriteALDBRecordModem


class Modem_ALDB(ALDB):

    def add_record(self, aldb):
        position = self._get_next_position()
        record = self.get_record(position)
        record.raw = aldb
        parsed_record = record.parse_record()
        # TODO if this is a PLM controller record, we may also know the
        # dev_cat sub_cat and firmware of this device, although they may
        # not be accurate.  Should we do something with this just in case
        # we are unable to reach the device such as motion sensors, remotes...
        self._device.add_device(BYTE_TO_ID(parsed_record['dev_addr_hi'],
                                           parsed_record['dev_addr_mid'],
                                           parsed_record['dev_addr_low']))

    def get_first_empty_addr(self):
        return self._get_next_position()

    def _get_next_position(self):
        position = 0
        records = self.get_all_records()
        for key in records.keys():
            if int(key) > position:
                position = int(key)
        position += 1
        position = str(position).zfill(4)
        return position

    def have_aldb_cache(self):
        # TODO This will return false for an empty aldb as well, do we care?
        ret = True
        if len(self.aldb) == 0:
            ret = False
        return ret


class Modem(Root):

    def __init__(self, core, **kwargs):
        self._devices = {}
        self.aldb = Modem_ALDB(self)
        self.trigger_mngr = Trigger_Manager(self)
        super().__init__(core, self, **kwargs)
        self._rcvd_handler = ModemRcvdHandler(self)
        self.send_handler = ModemSendHandler(self)
        for group_number in range(0x01, 0xFF):
            if self.get_object_by_group_num(group_number) is None:
                self.create_group(group_number, ModemGroup)
        self._read_buffer = bytearray()
        self._last_sent_msg = None
        self._msg_queue = []
        self._wait_to_send = 0
        self.port_active = True
        self.ack_time = 75
        self.attribute('base_group_number', 0x01)

    def _load_attributes(self, attributes):
        for name, value in attributes.items():
            if name == 'aldb':
                self.aldb.load_aldb_records(value)
            elif name == 'devices':
                self._load_devices(value)
            elif name == "groups":
                self._load_groups(value)
            elif name =='user_links':
                self._load_user_links(value)
            else:
                self.attribute(name, value)

    def _load_devices(self, devices):
        for dev_id, attributes in devices.items():
            self.add_device(dev_id, attributes=attributes)

    def _setup(self):
        self.update_device_classes()
        if self.dev_addr_str == '000000':
            self.send_command('plm_info')
        if self.aldb.have_aldb_cache() is False:
            self.query_aldb()

    ##############################################################
    #
    # User Accessible Functions
    #
    ##############################################################

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

    def delete_device(self, device_id):
        '''Removes a device from the Modems list of devices'''
        device_id = device_id.upper()
        if device_id in self._devices:
            device = self.core.get_device_by_addr(device_id)
            for group in device.get_all_groups():
                group.do_delete_callback()
            del self._devices[device_id]

    def port(self):
        return NotImplemented

    @property
    def wait_to_send(self):
        return self._wait_to_send

    @wait_to_send.setter
    def wait_to_send(self, value):
        if self._wait_to_send < time.time():
            self._wait_to_send = time.time()
        self._wait_to_send += value

    def get_device_by_addr(self, addr):
        ret = None
        if addr.lower() == self.dev_addr_str.lower():
            ret = self
        else:
            try:
                ret = self._devices[addr]
            except KeyError:
                # print('error, unknown device address=', addr)
                pass
        return ret

    def get_all_devices(self):
        ret = []
        for device in self._devices.values():
            ret.append(device)
        return ret

    def update_device_classes(self):
        pass

    def create_group(self, group_num, group_class):
        attributes = {}
        if group_num in self._groups_config:
            attributes = self._groups_config[group_num]
        if group_num >= 0x00 and group_num <= 0xFF:
            self._groups[group_num] = group_class(
                self, attributes=attributes)

    ##############################################################
    #
    # Internal Functions
    #
    ##############################################################

    def process_input(self):
        '''Called by the core loop. Reads available bytes from PLM, then parses
        the bytes into a message.  Do not call directly.'''
        self._read_from_port()
        self._advance_to_msg_start()
        read_bytes = self._parse_read_buffer()
        if read_bytes:
            self._process_inc_msg(read_bytes)

    def process_unacked_msg(self):
        '''Called by the core loop. Checks for unacked messages and queues them
        for resending.  Do not call directly.'''
        if self._is_ack_pending():
            msg = self._last_sent_msg
        else:
            return
        now = datetime.datetime.now().strftime("%M:%S.%f")
        # allow 75 milliseconds for the PLM to ack a message
        if msg.plm_ack is False:
            if msg.time_due < time.time() - (self.ack_time / 1000):
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
        '''Called by the core loop. Determines and sends the next message.
        Preferentially sends a message from the same device with the same
        state_machine as the perviously sent message.
        Otherwise, loops through all of the devices and sends the
        oldest message currently waiting in a device queue
        if there are no other conflicts. Do not call directly'''
        if (not self._is_ack_pending() and
                time.time() > self.wait_to_send):
            last_device = None
            send_msg = None
            if self._last_sent_msg:
                last_device = self._last_sent_msg.device
            if (last_device is not None and
                    last_device.queue.next_msg_create_time() is not None):
                send_msg = last_device.queue.pop_device_queue()
            else:
                devices = [self, ]
                msg_time = 0
                sending_device = False
                for device in self._devices.values():
                    devices.append(device)
                for device in devices:
                    dev_msg_time = device.queue.next_msg_create_time()
                    if dev_msg_time and (msg_time == 0 or
                                         dev_msg_time < msg_time):
                        sending_device = device
                        msg_time = dev_msg_time
                if sending_device:
                    send_msg = sending_device.queue.pop_device_queue()
            if send_msg:
                if send_msg.insteon_msg:
                    device = send_msg.device
                    device.last_sent_msg = send_msg
                self._send_msg(send_msg)

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
                index = self._read_buffer.find(bytes.fromhex('02'),1)
                del self._read_buffer[0:index]
        return ret

    def _read_from_port(self):
        return NotImplemented

    def _write_to_port(self, msg):
        return NotImplemented

    def _process_inc_msg(self, raw_msg):
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
                self._rcvd_handler._rcvd_plm_ack(msg)
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

    def _send_msg(self, msg):
        self._last_sent_msg = msg
        self._write(msg)

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

    def _write(self, msg):
        now = datetime.datetime.now().strftime("%M:%S.%f")
        if msg.insteon_msg:
            msg.insteon_msg._set_i2cs_checksum()
        if self.port_active:
            print(now, 'sending data', BYTE_TO_HEX(msg.raw_msg))
            msg.time_sent = time.time()
            self._write_to_port(msg.raw_msg)
        else:
            msg.failed = True
            print(
                now,
                'Error: the modem on port',
                self.port,
                'is not active, unable to send message'
            )
        return


class ModemGroup(Group):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)

    def create_controller_link_sequence(self, user_link):
        '''Creates a controller link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        link_sequence = WriteALDBRecordModem(group=self)
        link_sequence.controller = True
        link_sequence.linked_group = user_link.responder_group
        return link_sequence

    def create_responder_link_sequence(self, user_link):
        # TODO Is the modem ever a responder in a way that this would be needed?
        return NotImplemented

    def _state_commands(self):
        on_plm_bytes = {
            'group': self.group_number,
            'cmd_1': 0x11,
            'cmd_2': 0x00,
        }
        on_message = PLM_Message(self.device.plm,
                                 plm_cmd='all_link_send',
                                 plm_bytes=on_plm_bytes)
        off_plm_bytes = {
            'group': self.group_number,
            'cmd_1': 0x13,
            'cmd_2': 0x00,
        }
        off_message = PLM_Message(self.device.plm,
                                  plm_cmd='all_link_send',
                                  plm_bytes=off_plm_bytes)
        ret = {
            'ON': on_message,
            'OFF': off_message
        }
        return ret

    def set_state(self, state):
        commands = self._state_commands()
        try:
            message = commands[state.upper()]
        except KeyError:
            print('This group doesn\'t know the state', state)
        else:
            message.state_machine = 'all_link_send'
            records = self.device.plm.aldb.get_matching_records({
                'controller': True,
                'group': self.group_number,
                'in_use': True
            })
            # Until all link status is complete, sending any other cmds to PLM
            # will cause it to abandon all link process
            message.seq_lock = True
            # Time with retries for failed objects, plus we actively end it on
            # success
            wait_time = (len(records) + 1) * (87 / 1000 * 18)
            message.seq_time = wait_time
            message.extra_ack_time = wait_time
            self.device.plm.queue_device_msg(message)

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = super().get_features()
        ret['responder'] = False
        return ret
