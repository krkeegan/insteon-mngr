'''The classes for the queue system that tracks and orders the messages
sent to the device.'''

import time
import datetime
from collections import UserList, UserDict

class QueueManager(UserDict):
    '''A simple dict like object that acts as the central repository for the
    various queues for each device.'''
    def __init__(self, device):
        super().__init__()
        self._device = device
        self._device_msg_queue = {}
        self.data['default'] = Queue(self)
        self._current_queue = self.data['default']

    def __delitem__(self, key):
        if key != 'default': # Add other protected queues
            print('removing', key, 'queue')
            del self.data[key]
        self._check_current_queue()


    def __missing__(self, key):
        self.data[key] = Queue(self)
        return self.data[key]

    def _check_current_queue(self):
        if self._current_queue.name == 'default':
            # Always check for other queues besides default
            self._current_queue = self._get_next_state_machine()
        elif self._current_queue.expire_time <= time.time():
            now = datetime.datetime.now().strftime("%M:%S.%f")
            print(now, self._current_queue.name, "state expired")
            self._current_queue = self._get_next_state_machine()

    def _get_next_state_machine(self):
        next_state_name = 'default'
        msg_time = time.time() + 1 #ensures a time in the future
        for name, queue in self.data.items():
            if name != 'default' and len(queue):
                test_time = queue[0].creation_time
                if test_time and test_time < msg_time:
                    next_state_name = name
                    msg_time = test_time
        return self.data[next_state_name]

    def get_queue_name(self, queue):
        '''Returns the name of the passed queue.'''
        ret = None
        for name, test_queue in self.data.items():
            if queue == test_queue:
                ret = name
                break
        return ret

    def pop_device_queue(self):
        '''Returns and removes the next message in the queue.  Returns None if
        no message exists.'''
        ret = None
        self._check_current_queue()
        if len(self._current_queue) > 0:
            ret = self._current_queue.pop(0)
            self._device.update_message_history(ret)
            self._current_queue.expire_time = time.time()
        return ret

    def next_msg_create_time(self):
        '''Returns the creation time of the message to be sent in the queue'''
        ret = None
        self._check_current_queue()
        try:
            ret = self._current_queue[0].creation_time
        except (KeyError, IndexError):
            pass
        return ret


class Queue(UserList):
    '''The basic outgoing message queue for a device.'''
    def __init__(self, manager, *args):
        super().__init__(*args)
        self._manager = manager
        self._keep_alive = 8
        self._expire_time = time.time() + self._keep_alive

    @property
    def expire_time(self):
        '''Returns the timestamp when this queue will expire.'''
        return self._expire_time

    @expire_time.setter
    def expire_time(self, value):
        self._expire_time = value + self._keep_alive

    @property
    def name(self):
        '''Returns the name of this Queue'''
        return self._manager.get_queue_name(self)
