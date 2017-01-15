import time
import datetime
import pprint


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

    def _queue_device_msg(self, message, state):
        if state == '':
            state = 'default'
        if state not in self._device_msg_queue:
            self._device_msg_queue[state] = []
        self._device_msg_queue[state].append(message)

    def _resend_msg(self, message):
        # This is a bit of a hack, assumes the state has not changed
        # Maybe move state to the message class?
        state = self.state_machine
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
        if self.state_machine in self._device_msg_queue and \
                self._device_msg_queue[self.state_machine]:
            ret = self._device_msg_queue[self.state_machine][0].creation_time
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
            if name == 'ALDB':
                self._aldb.load_aldb_records(value)
            elif name == 'Devices':  # should only be plm?
                self._load_devices(value)
            else:
                self.attribute(name, value)

    def _load_devices(self, devices):
        for id, attributes in devices.items():
            self.add_device(id, attributes=attributes)


class Root_Insteon(Base_Device):

    def __init__(self, core, plm, **kwargs):
        self._groups = []
        super().__init__(core, plm, **kwargs)

    def create_group(self, group_num, Group_Class):
        self._groups.append(Group_Class(self, group_num))

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
