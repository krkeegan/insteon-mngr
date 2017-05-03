import time
import datetime
import pprint

from insteon_mngr import ID_STR_TO_BYTES, BYTE_TO_HEX
from insteon_mngr.user_link import UserLink
from insteon_mngr.sequences import (WriteALDBRecordi2, WriteALDBRecordi1)

class Common(object):
    '''The base class inherited by groups and devices, primarily provides
    functions associated with saving the state.'''
    def __init__(self, **kwargs):
        self._attributes = {}
        if 'attributes' in kwargs and kwargs['attributes'] is not None:
            self._load_attributes(kwargs['attributes'])

    def _load_attributes(self, attributes):
        for name, value in attributes.items():
            self.attribute(name, value)

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

    def get_attributes(self):
        ret = self._attributes.copy()
        return ret

    def get_features_and_attributes(self):
        ret = self.get_attributes()
        return ret


class Group(Common):
    '''The Group class for all groups.  Specialized functions should be done
    in the send_handler or functions.'''
    def __init__(self, device, **kwargs):
        super().__init__(**kwargs)
        self._device = device
        self._type = 'relay'
        self._update_callbacks = []
        self._delete_callbacks = []

    @property
    def type(self):
        '''Returns the type of device group that this group is.'''
        return self._type

    @property
    def group_number(self):
        ret = self._device.get_group_number_by_object(self)
        if ret is not None:
            ret = int(ret)
        return ret

    @property
    def device(self):
        return self._device

    @property
    def state(self):
        '''Returns the cached state of the device.'''
        return self.attribute('state')

    def set_cached_state(self, value):
        '''Update the internal tracking state of the device, likely you don't
        want to call this'''
        self.attribute(attr='state', value=value)
        self.attribute(attr='state_time', value=time.time())
        self._do_update_callback()

    def _state_commands(self):
        ret = {
            'ON': self.device.create_message('on'),
            'OFF': self.device.create_message('off')
        }
        return ret

    def set_state(self, state):
        commands = self._state_commands()
        state = str(state)
        try:
            msg = commands[state.upper()]
        except KeyError:
            print('This group doesn\'t know the state', state)
        else:
            self.device.queue_device_msg(msg)

    @property
    def state_age(self):
        '''Returns the age in seconds of the state value.'''
        return time.time() - self.attribute('state_time')

    def _do_update_callback(self):
        for callback in self._update_callbacks:
            callback()

    @property
    def name(self):
        name = self.attribute('name')
        if name is None:
            name = ''
        return name

    @name.setter
    def name(self, value):
        return self.attribute('name', value)

    def _get_undefined_responder(self):
        ret = []
        attributes = {
            'in_use': True,
            'responder': True,
            'group': self.group_number,
            'dev_addr_hi': self.device.dev_addr_hi,
            'dev_addr_mid': self.device.dev_addr_mid,
            'dev_addr_low': self.device.dev_addr_low
        }
        aldb_responder_links = self.device.core.get_matching_aldb_records(attributes)
        for aldb_link in aldb_responder_links:
            if (len(aldb_link.get_reciprocal_records()) == 0 and
                    aldb_link.is_a_defined_link() is False):
                # A responder link exists on the device, this will be listed
                # in the undefined controller function already
                ret.append(aldb_link)
        return ret

    def _get_undefined_controller(self):
        ret = []
        attributes = {
            'in_use': True,
            'controller': True,
            'group': self.group_number
        }
        aldb_controller_links = self.device.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if (aldb_link.is_a_defined_link() is False and
                    aldb_link.linked_device is not None and # Unknown Link
                    aldb_link.linked_device is not self.device.plm # plm link
               ):
                ret.append(aldb_link)
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
        aldb_controller_links = self.device.aldb.get_matching_records(attributes)
        for aldb_link in aldb_controller_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        attributes = {
            'in_use': True,
            'responder': True,
            'data_3': self.group_number
        }
        aldb_responder_links = self.device.aldb.get_matching_records(attributes)
        for aldb_link in aldb_responder_links:
            if aldb_link.linked_device is None:
                ret.append(aldb_link)
        return ret

    def get_features_and_attributes(self):
        ret = self.get_attributes()
        ret.update(self.get_features())
        return ret

    def create_controller_link_sequence(self, user_link):
        '''Creates a controller link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        if self.device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(group=self)
        else:
            link_sequence = WriteALDBRecordi1(group=self)
        if user_link.controller_key is not None:
            link_sequence.key = user_link.controller_key
        link_sequence.controller = True
        link_sequence.linked_group = user_link.responder_group
        link_sequence.data1 = self.device.get_controller_data1(None)
        link_sequence.data2 = self.device.get_controller_data2(None)
        return link_sequence

    def create_responder_link_sequence(self, user_link):
        '''Creates a responder link sequence based on a passed user_link,
        returns the link sequence, which needs to be started'''
        if self.device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(group=self)
        else:
            link_sequence = WriteALDBRecordi1(group=self)
        if user_link.responder_key is not None:
            link_sequence.key = user_link.responder_key
        link_sequence.controller = False
        link_sequence.linked_group = user_link.controller_group
        link_sequence.data1 = user_link.data_1
        link_sequence.data2 = user_link.data_2
        return link_sequence

    def state_str(self):
        '''Returns the current state of the device in a human readable form'''
        # TODO do we want to return an unknown value? trigger status if not?
        ret = 'OFF'
        if self.state == 0xFF:
            ret = 'ON'
        return ret

    def state_bool(self):
        ret = False
        if self.state == 0xFF:
            ret = True
        return ret

    def add_update_callback(self, callback):
        """Register as callback for when state is touched."""
        self._update_callbacks.append(callback)

    def add_delete_callback(self, callback):
        """Register as callback for when this group is deleted."""
        self._delete_callbacks.append(callback)

    def do_delete_callback(self):
        for callback in self._delete_callbacks:
            callback()

    def list_data_1_options(self):
        return {'ON': 0xFF,
                'OFF': 0x00}

    def list_data_2_options(self):
        return {'None': 0x00}

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {
            'responder': True,
        }
        ret['data_1'] = {
            'name': 'On/Off',
            'default': 0xFF,
            'values': self.list_data_1_options()
        }
        ret['data_2'] = {
            'name': 'None',
            'default': 0x00,
            'values': self.list_data_2_options()
        }
        return ret


class BaseSendHandler(object):
    '''Provides a shell of the functions that all send handlers must support'''

    def __init__(self, device):
        '''The base send handler object inherited by all send handlers'''
        self._device = device

    def create_message(self, command_name):
        '''Creates a message object based on the command_name passed'''
        return NotImplemented

    def send_command(self, command_name, state=''):
        '''Creates a message based on the command_name and queues it to be sent
        to the device using the state_machine of state of defined'''
        return NotImplemented

    def query_aldb(self):
        '''Initiates the process to query the all link database on the device'''
        return NotImplemented


class Root(Common):
    '''The root object of an insteon device, inherited by Devices and Modems'''
    def __init__(self, core, plm, **kwargs):
        self._groups = {}
        self._groups_config = {}
        self._user_links = {}
        self._core = core
        self._plm = plm
        super().__init__(**kwargs)
        self._state_machine = 'default'
        self._state_machine_time = 0
        self._device_msg_queue = {}
        self._out_history = []
        self._id_bytes = bytearray(3)
        self.send_handler = BaseSendHandler(self)
        if 'device_id' in kwargs:
            self._id_bytes = ID_STR_TO_BYTES(kwargs['device_id'])
        if self.attribute('base_group_number') is None:
            self.attribute('base_group_number', 0x00)

    @property
    def root(self):
        return self

    @property
    def base_group_number(self):
        return self.attribute('base_group_number')

    @property
    def base_group(self):
        return self.get_object_by_group_num(self.base_group_number)

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

    def _load_groups(self, value):
        for group_number, attributes in value.items():
            self._groups_config[int(group_number)] = attributes

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
            if user_link.controller_group_number not in ret[user_link.controller_id]:
                ret[user_link.controller_id][user_link.controller_group_number] = []
            ret[user_link.controller_id][user_link.controller_group_number].append(user_link.data)
        return ret

    def save_groups(self):
        '''Constructs a dictionary of the group attributes for saving to the
        config file
        Returns:None'''
        ret = self._groups_config
        for group in self.get_all_groups():
            ret[group.group_number] = group._attributes.copy()
        return ret

    def get_bad_links(self):
        result = []
        result.extend(self._bad_controller())
        result.extend(self._bad_responder())
        result.extend(self._bad_unknown())
        ret = []
        for link in result:
            if link not in ret:
                ret.append(link)
        return ret

    def _bad_controller(self):
        # Controller link on this device is associated with an unkown group
        # Any or no type of responder on other device
        ret = []
        attributes = {
            'in_use': True,
            'controller': True
        }
        records = self.aldb.get_matching_records(attributes)
        for aldb_record in records:
            if aldb_record.parse_record()['group'] not in self._groups:
                ret.append(aldb_record)
        return ret

    def _bad_responder(self):
        # No Controller link on this device
        # Responder link on another device to an unkown group on this device
        ret = []
        attributes = {
            'in_use': True,
            'responder': True,
            'dev_addr_hi': self.dev_addr_hi,
            'dev_addr_mid': self.dev_addr_mid,
            'dev_addr_low': self.dev_addr_low
        }
        records = self.core.get_matching_aldb_records(attributes)
        for aldb_record in records:
            if aldb_record.parse_record()['group'] not in self._groups:
                ret.append(aldb_record)
        return ret

    def _bad_unknown(self):
        # Responder link on this device is associated with an unknown group
        # Controller is unknown
        ret = []
        attributes = {
            'in_use': True,
            'responder': True,
        }
        records = self.aldb.get_matching_records(attributes)
        for aldb_record in records:
            if aldb_record.linked_device is None:
                # If the linked device exists, then this record will show up
                # as an unknown device on the linked device's page
                ret.append(aldb_record)
        return ret

    ##################################
    # Public functions
    ##################################

    def add_user_link(self, controller_group, data, uid):
        controller_id = controller_group.device.dev_addr_str
        group_number = controller_group.group_number
        found = False
        for user_link in self._user_links.values():
            if (controller_id == user_link.controller_id and
                    group_number == user_link.controller_group_number and
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
                uid
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


    # TODO this whole create_group seems like it needs a bit of a rework
    # TODO we are not deleting erroneous groups
    def create_group(self, group_num, group_class):
        attributes = {}
        if group_num in self._groups_config:
            attributes = self._groups_config[group_num]
        if self.get_object_by_group_num(group_num) is None:
            if group_num == 0x00 or group_num == 0x01:
                self._change_base_group_number(group_num, group_class, attributes)
            elif group_num >= 0x02 and group_num <= 0xFF:
                self._groups[group_num] = group_class(self, attributes=attributes)
        elif type(self.get_object_by_group_num(group_num)) is not group_class:
            self._promote_group(group_num, group_class, attributes)
        self.core.do_group_callback(self.get_object_by_group_num(group_num))

    def _promote_group(self, group_num, group_class, attributes):
        attributes.update(self.get_object_by_group_num(group_num).get_attributes())
        self._groups[group_num] = group_class(self, attributes=attributes)

    def _change_base_group_number(self, group_num, group_class, attributes):
        # For base groups we only have 1 or the other and copy from
        # one to the other on changes
        old_group = 0x00
        if group_num == 0x00:
            old_group = 0x01
        if self.get_object_by_group_num(old_group) is not None:
            # there is a potential for overwriting if both somehow
            # exist
            self._groups[group_num] = self._groups[old_group]
            del self._groups[old_group]
            #TODO should we delete the old_group from the _groups_config as well\
            #TODO Do we need to be loading the data from _groups_config
            #TODO do we need to call the delete group callback here
        else:
            self._groups[group_num] = group_class(self, attributes=attributes)

    def get_object_by_group_num(self, search_num):
        ret = None
        if search_num in self._groups:
            ret = self._groups[search_num]
        return ret

    def get_group_number_by_object(self, search_object):
        ret = None
        for key, value in self._groups.items():
            if value == search_object:
                ret = key
        return ret

    def get_all_groups(self):
        return self._groups.values()

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

    def create_message(self, command_name):
        return self.send_handler.create_message(command_name)

    def send_command(self, command_name, state=''):
        return self.send_handler.send_command(command_name, state)

    def query_aldb(self):
        return self.send_handler.query_aldb()
