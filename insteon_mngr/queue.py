'''The classes for the queue system that tracks and orders the messages
sent to the device.'''

import time
from collections import UserList


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
