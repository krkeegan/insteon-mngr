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

    def controller_device(self):
        '''Returns the controller device of this link or None if it does not
        exist'''
        root = self._core.get_device_by_addr(self._address)
        ret = None
        if root is not None:
            ret = root.get_object_by_group_num(self._group)
        return ret

    def matches_aldb(self, aldb_record):
        '''Returns true if the aldb_record passed is either the controller or
        responder aldb record of this user link else false'''
        # We are not checking data_1-3 here should we be?
        ret = False
        aldb_parsed = aldb_record.parse_record()
        if aldb_record.linked_device is not None:
            linked_addr = aldb_record.linked_device.root.dev_addr_str
            record_addr = aldb_record.device.root.dev_addr_str
            if (aldb_parsed['group'] == self._group and
                aldb_parsed['in_use'] == True):
                if (aldb_parsed['controller'] is True and
                    linked_addr == self._device.dev_addr_str):
                    ret = True
                elif(aldb_parsed['controller'] is False and
                     record_addr == self._device.dev_addr_str):
                    ret = True
        return ret
