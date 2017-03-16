'''The user_link classes'''

class UserLink(object):
    '''The base class for user_links'''

    def __init__(self, device, reciprocal_id, group_number, data):
        self._device = device
        self._core = device.root.core
        self._address = reciprocal_id
        self._group = int(group_number)
        self._data_1 = data['data_1']
        self._data_2 = data['data_2']
        self._data_3 = data['data_3']

    def matches(self, device):
        '''Returns true if the device passed is the reciprocal controller device
        of this link else false'''
        ret = False
        if (device.root.dev_addr_str.lower() == self._address.lower() and
            self._group == device.group_number):
            ret = True
        return ret
