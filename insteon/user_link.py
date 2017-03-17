'''The user_link classes'''

from insteon import BYTE_TO_ID

class UserLink(object):
    '''The base class for user_links'''

    def __init__(self, device, reciprocal_id, group_number, data):
        self._device = device
        self._core = device.root.core
        self._address = reciprocal_id.upper()
        self._group = int(group_number)
        self._data_1 = data['data_1']
        self._data_2 = data['data_2']
        self._data_3 = data['data_3']

    def matches_device(self, device):
        '''Returns true if the device passed is the reciprocal controller device
        of this link else false'''
        ret = False
        if (device.root.dev_addr_str == self._address and
            self._group == device.group_number):
            ret = True
        return ret

    def matches_aldb(self, aldb_link):
        '''Returns true if the aldb_link passed is the reciprocal controller
        link of this link else false'''
        ret = False
        aldb_parsed = aldb_link.parse_record()
        controller_dev_addr = BYTE_TO_ID(aldb_parsed['dev_addr_hi'],
                                         aldb_parsed['dev_addr_mid'],
                                         aldb_parsed['dev_addr_low'])
        responder_dev_addr = aldb_link.device.dev_addr_str
        if (aldb_parsed['group'] == self._group and
            aldb_parsed['in_use'] == True):
            if (aldb_parsed['controller'] is True and
                controller_dev_addr == self._device.dev_addr_str):
                ret = True
            elif(responder_dev_addr == self._device.dev_addr_str):
                ret = True
        return ret
