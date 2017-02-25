import time
import datetime
import pprint
import binascii


def BYTE_TO_HEX(data):
    '''Takes a bytearray or a byte and returns a string
    representation of the hex value'''
    return binascii.hexlify(data).decode().upper()

def BYTE_TO_ID(high, mid, low):
    # pylint: disable=E1305
    ret = ('{:02x}'.format(high, 'x').upper() +
           '{:02x}'.format(mid, 'x').upper() +
           '{:02x}'.format(low, 'x').upper())
    return ret

def ID_STR_TO_BYTES(dev_id_str):
    ret = bytearray(3)
    ret[0] = (int(dev_id_str[0:2], 16))
    ret[1] = (int(dev_id_str[2:4], 16))
    ret[2] = (int(dev_id_str[4:6], 16))
    return ret

# This is here because the above functions are imported in these
# consider some other structure to avoid what is clearly a bad import
from insteon.devices import (GroupSendHandler, GroupFunctions)

class Base_Device(object):

    def __init__(self, core, plm, **kwargs):
        self._core = core
        self._plm = plm
        self._state_machine = 'default'
        self._state_machine_time = 0
        self._device_msg_queue = {}
        self._attributes = {}
        self._out_history = []
        if 'attributes' in kwargs:
            self._load_attributes(kwargs['attributes'])

    @property
    def core(self):
        return self._core

    @property
    def plm(self):
        return self._plm

    @property
    def state_machine(self):
        '''The state machine tracks the 'state' that the device is in.
        This is necessary because Insteon is not a stateless protocol,
        interpreting some incoming messages requires knowing what
        commands were previously issued to the device.

        Whenever a state is set, only messages of that state will be
        sent to the device, all other messages will wait in a queue.
        To avoid locking up a device, a state will automatically be
        eliminated if it has not been updated within 8 seconds. You
        can update a state by calling update_state_machine or sending
        a command with the appropriate state value'''
        if self._state_machine_time <= (time.time() - 8) or \
                self._state_machine == 'default':
            # Always check for states other than default
            if self._state_machine != 'default':
                now = datetime.datetime.now().strftime("%M:%S.%f")
                print(now, self._state_machine, "state expired")
                pprint.pprint(self._device_msg_queue)
            self._state_machine = self._get_next_state_machine()
            if self._state_machine != 'default':
                self._state_machine_time = time.time()
        return self._state_machine

    def _get_next_state_machine(self):
        next_state = 'default'
        msg_time = 0
        for state in self._device_msg_queue:
            if state != 'default' and self._device_msg_queue[state]:
                test_time = self._device_msg_queue[state][0].creation_time
                if test_time and (msg_time == 0 or test_time < msg_time):
                    next_state = state
                    msg_time = test_time
        return next_state

    def remove_state_machine(self, value):
        if value == self.state_machine:
            print('finished', self.state_machine)
            self._state_machine = 'default'
            self._state_machine_time = time.time()
        else:
            print(value, 'was not the active state_machine')

    def update_state_machine(self, value):
        if value == self.state_machine:
            self._state_machine_time = time.time()
        else:
            print(value, 'was not the active state_machine')

    def queue_device_msg(self, message):
        if message.state_machine not in self._device_msg_queue:
            self._device_msg_queue[message.state_machine] = []
        self._device_msg_queue[message.state_machine].append(message)

    def _resend_msg(self, message):
        state = message.state_machine
        if state not in self._device_msg_queue:
            self._device_msg_queue[state] = []
        self._device_msg_queue[state].insert(0, message)
        self._state_machine_time = time.time()

    def pop_device_queue(self):
        '''Returns and removes the next message in the queue'''
        ret = None
        if self.state_machine in self._device_msg_queue and \
                self._device_msg_queue[self.state_machine]:
            ret = self._device_msg_queue[self.state_machine].pop(0)
            self._update_message_history(ret)
            self._state_machine_time = time.time()
        return ret

    def next_msg_create_time(self):
        '''Returns the creation time of the message to be sent in the queue'''
        ret = None
        try:
            ret = self._device_msg_queue[self.state_machine][0].creation_time
        except (KeyError, IndexError):
            pass
        return ret

    def _update_message_history(self, msg):
        # Remove old messages first
        archive_time = time.time() - 120
        last_msg_to_del = 0
        for search_msg in self._out_history:
            if search_msg.time_sent < archive_time:
                last_msg_to_del += 1
            else:
                break
        if last_msg_to_del:
            del self._out_history[0:last_msg_to_del]
        # Add this message onto the end
        self._out_history.append(msg)

    def search_last_sent_msg(self, **kwargs):
        '''Return the most recently sent message of this type
        plm_cmd or insteon_cmd'''
        ret = None
        if 'plm_cmd' in kwargs:
            for msg in reversed(self._out_history):
                if msg.plm_cmd_type == kwargs['plm_cmd']:
                    ret = msg
                    break
        elif 'insteon_cmd' in kwargs:
            for msg in reversed(self._out_history):
                if msg.insteon_msg and \
                      msg.insteon_msg.device_cmd_name == kwargs['insteon_cmd']:
                    ret = msg
                    break
        return ret

    def attribute(self, attr, value=None):
        if value is not None:
            self._attributes[attr] = value
        try:
            ret = self._attributes[attr]
        except KeyError:
            ret = None
        return ret

    def _load_attributes(self, attributes):
        for name, value in attributes.items():
            self.attribute(name, value)

class Base_Insteon(Base_Device):

    def __init__(self, core, plm, **kwargs):
        self._id_bytes = bytearray(3)
        if 'device_id' in kwargs:
            self._id_bytes = ID_STR_TO_BYTES(kwargs['device_id'])
        super().__init__(core, plm, **kwargs)

    @property
    def dev_addr_hi(self):
        return self._id_bytes[0]

    @property
    def dev_addr_mid(self):
        return self._id_bytes[1]

    @property
    def dev_addr_low(self):
        return self._id_bytes[2]

    @property
    def dev_addr_str(self):
        ret = BYTE_TO_HEX(
            bytes([self.dev_addr_hi, self.dev_addr_mid, self.dev_addr_low]))
        return ret

    @property
    def dev_cat(self):
        dev_cat = self.attribute('dev_cat')
        if dev_cat is None:
            dev_cat = 0x00
        return dev_cat

    @property
    def sub_cat(self):
        sub_cat = self.attribute('sub_cat')
        if sub_cat is None:
            sub_cat = 0x00
        return sub_cat

    @property
    def firmware(self):
        firmware = self.attribute('firmware')
        if firmware is None:
            firmware = 0x00
        return firmware

    @property
    def engine_version(self):
        return self.attribute('engine_version')

    @property
    def group(self):
        return NotImplemented

    @property
    def state(self):
        '''Returns the cached state of the device.'''
        return self.attribute('state')

    @state.setter
    def state(self, value):
        self.attribute(attr='state', value=value)
        self.attribute(attr='state_time', value=time.time())

    @property
    def state_age(self):
        '''Returns the age in seconds of the state value.'''
        return time.time() - self.attribute('state_time')


class Root_Insteon(Base_Insteon):
    '''The base of the primary group'''

    def __init__(self, core, plm, **kwargs):
        self._groups = []
        super().__init__(core, plm, **kwargs)

    def create_group(self, group_num, group):
        device_id = self.dev_addr_str
        if group_num > 0x01 and group_num <= 0xFF:
            self._groups.append(group(
                self, group_num, device_id=device_id))

    def get_object_by_group_num(self, search_num):
        ret = None
        if search_num == 0x00 or search_num == 0x01:
            ret = self
        else:
            for group_obj in self._groups:
                if group_obj.group_number == search_num:
                    ret = group_obj
                    break
        return ret

    def get_all_groups(self):
        return self._groups.copy()

    @property
    def group(self):
        return 0x01

    @property
    def user_links(self):
        ret = None
        if self.attribute('user_links') is not None:
            ret = {}
            records = self.attribute('user_links')
            for device in records.keys():
                ret[device] = {}
                for group in records[device].keys():
                    ret[device][int(group)] = records[device][group]
        return ret

    @user_links.setter
    def user_links(self, records):
        self.attribute('user_links', records)

    def set_dev_addr(self, addr):
        self._id_bytes = ID_STR_TO_BYTES(addr)
        return

    def set_dev_version(self, dev_cat=None, sub_cat=None, firmware=None):
        self.attribute('dev_cat', dev_cat)
        self.attribute('sub_cat', sub_cat)
        self.attribute('firmware', firmware)
        self.update_device_classes()
        return

    def update_device_classes(self):
        # pylint: disable=R0201
        return NotImplemented

    def export_links(self):
        # pylint: disable=E1101
        records = {}
        for key in self.aldb.get_all_records().keys():
            parsed = self.aldb.parse_record(key)
            if parsed['in_use'] and not parsed['controller']:
                linked_device = self.aldb.get_linked_obj(key)
                name = self.aldb.get_linked_device_str(key)
                group = parsed['group']
                group = 0x01 if group == 0x00 else group
                if group == 0x01 and linked_device is self.plm:
                    # ignore i2cs required links
                    continue
                if name not in records.keys():
                    records[name] = {}
                if group not in records[name].keys():
                    records[name][group] = []
                for entry in records[name][group]:
                    # ignore duplicates
                    if (entry['data_1'] == parsed['data_1'] and
                            entry['data_2'] == parsed['data_2'] and
                            entry['data_3'] == parsed['data_3']):
                        continue
                records[name][group].append({
                    'data_1': parsed['data_1'],
                    'data_2': parsed['data_2'],
                    'data_3': parsed['data_3']
                })
        if self.user_links is not None:
            new_records = records
            records = self.user_links
            records.update(new_records)
        self.user_links = records


class InsteonGroup(Base_Insteon):

    def __init__(self, parent, group_number, **kwargs):
        self._parent = parent
        super().__init__(self._parent.core, self._parent.plm, **kwargs)
        self._group_number = group_number
        self.send_handler = GroupSendHandler(self)
        self.functions = GroupFunctions(self)

    @property
    def group_number(self):
        return self._group_number

    @property
    def parent(self):
        return self._parent

    @property
    def dev_cat(self):
        return self._parent.dev_cat

    @property
    def sub_cat(self):
        return self._parent.sub_cat

    @property
    def firmware(self):
        return self._parent.firmware

    @property
    def engine_version(self):
        return self._parent.engine_version

    def set_dev_addr(self, *args, **kwargs):
        # pylint: disable=W0613
        return NotImplemented

    def set_dev_version(self, *args, **kwargs):
        # pylint: disable=W0613
        return NotImplemented
