import time
import datetime
import pprint
import binascii
from insteon.user_link import UserLink


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

class Group(object):
    '''The base class.  All groups inherit this, the root group gets a lot more
    functions.  Specialized groups can modify or add functions in classes that
    inherit this.'''
    def __init__(self, root, group_number, **kwargs):
        self._root = root
        self._group_number = group_number
        self._attributes = {}
        if 'attributes' in kwargs and kwargs['attributes'] is not None:
            self._load_attributes(kwargs['attributes'])
        self.send_handler = GroupSendHandler(self)
        self.functions = GroupFunctions(self)

    @property
    def group_number(self):
        return self._group_number

    @property
    def root(self):
        return self._root

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

    @property
    def name(self):
        name = self.attribute('name')
        if name is None:
            name = ''
        return name

    @name.setter
    def name(self, value):
        return self.attribute('name', value)

    def _load_attributes(self, attributes):
        for name, value in attributes.items():
            self.attribute(name, value)

    def _get_undefined_responder(self):
        ret = []
        attributes = {
            'in_use': True,
            'responder': True,
            'group': self.group_number,
            'dev_addr_hi': self.root.dev_addr_hi,
            'dev_addr_mid': self.root.dev_addr_mid,
            'dev_addr_low': self.root.dev_addr_low
        }
        aldb_responder_links = self.root.core.get_matching_aldb_records(attributes)
        for aldb_link in aldb_responder_links:
            if (len(aldb_link.get_reciprocal_records()) == 0 and
                aldb_link.is_a_defined_link() is False):
                # A responder link exists on the device, this will be listed
                # in the undefined controller function
                ret.append(aldb_link)
        return ret

    def _get_undefined_controller(self):
        ret = []
        attributes = {
            'in_use': True,
            'controller': True,
            'group': self.group_number
        }
        aldb_controller_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if (aldb_link.is_a_defined_link() is False and
                aldb_link.linked_device is not None and # Unknown Link
                aldb_link.linked_device is not self._root.plm # plm link
                ):
                ret.append(aldb_link)
        return ret

    def attribute(self, attr, value=None):
        '''An attribute is a characteristic of an object that is not intrinsic
        to the nature of device. This includes dev_cat and related items as well
        as the object state.  Attribute excludes things like whether the object is a
        responder or is_deaf, these are features.'''
        if value is not None:
            self._attributes[attr] = value
        try:
            ret = self._attributes[attr]
        except KeyError:
            ret = None
        return ret

    def get_undefined_links(self):
        ret = []
        # 1 Undefined Controllers on This Device
        ret.extend(self._get_undefined_controller())
        # 2 Orphaned Undefined Responders on Other Devices
        ret.extend(self._get_undefined_responder())
        return ret

    def get_unknown_device_links(self):
        '''Returns all links on the device which do not associated with a
        known device'''
        ret = []
        attributes = {
            'in_use': True,
            'controller': True,
            'group': self.group_number
        }
        aldb_controller_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        attributes = {
            'in_use': True,
            'responder': True,
            'data_3': self.group_number
        }
        aldb_responder_links = self.root.aldb.get_matching_records(attributes)
        for aldb_link in aldb_responder_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        return ret

    def get_attributes(self):
        ret = self._attributes.copy()
        return ret

    def get_features_and_attributes(self):
        ret = self.get_attributes()
        ret.update(self.functions.get_features())
        return ret


class Root(Group):
    '''The root object of an insteon device, inherited by Devices and Modems'''
    def __init__(self, core, plm, **kwargs):
        self._core = core
        self._plm = plm
        self._state_machine = 'default'
        self._state_machine_time = 0
        self._device_msg_queue = {}
        self._out_history = []
        self._id_bytes = bytearray(3)
        self._groups = []
        self._user_links = {}
        if 'device_id' in kwargs:
            self._id_bytes = ID_STR_TO_BYTES(kwargs['device_id'])
        super().__init__(self, 0x01, **kwargs)

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
        return dev_cat

    @property
    def sub_cat(self):
        sub_cat = self.attribute('sub_cat')
        return sub_cat

    @property
    def firmware(self):
        firmware = self.attribute('firmware')
        return firmware

    @property
    def engine_version(self):
        return self.attribute('engine_version')

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

    ##################################
    # Private functions
    ##################################

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

    def _resend_msg(self, message):
        state = message.state_machine
        if state not in self._device_msg_queue:
            self._device_msg_queue[state] = []
        self._device_msg_queue[state].insert(0, message)
        self._state_machine_time = time.time()

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

    def _load_user_links(self, links):
        for controller_id, groups in links.items():
            for group_number, all_data in groups.items():
                for data in all_data:
                    user_link = UserLink(
                        self,
                        controller_id,
                        group_number,
                        data,
                        None
                    )
                    self._user_links[user_link.uid] = user_link

    def save_user_links(self):
        '''Constructs a dictionary for saving the user links to the config
        file'''
        ret = {}
        for user_link in self._user_links.values():
            if user_link.controller_id not in ret:
                ret[user_link.controller_id] = {}
            if user_link.group not in ret[user_link.controller_id]:
                ret[user_link.controller_id][user_link.group] = []
            ret[user_link.controller_id][user_link.group].append(user_link.data)
        return ret



    ##################################
    # Public functions
    ##################################

    def add_user_link(self, controller_device, data, uid):
        controller_id = controller_device.root.dev_addr_str
        group_number = controller_device.group_number
        found = False
        for user_link in self._user_links.values():
            if (controller_id == user_link.controller_id and
                group_number == user_link.group and
                data['data_1'] == user_link.data_1 and
                data['data_2'] == user_link.data_2 and
                data['data_3'] == user_link.data_3):
                found = True
                break
        if not found:
            new_user_link = UserLink(
                self,
                controller_id,
                group_number,
                data,
                None
            )
            self._user_links[new_user_link.uid] = new_user_link

    def get_all_user_links(self):
        return self._user_links.copy()

    def delete_user_link(self, uid):
        ret = True
        try:
            del self._user_links[uid]
        except KeyError:
            ret = False
        return ret

    def find_user_link(self, search_uid):
        ret = None
        for link_uid in self._user_links:
            if search_uid == link_uid:
                ret = self._user_links[link_uid]
        return ret

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

    def create_group(self, group_num, group, attributes=None):
        if group_num > 0x01 and group_num <= 0xFF:
            self._groups.append(group(self, group_num, attributes=attributes))

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
