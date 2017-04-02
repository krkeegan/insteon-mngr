'''The user_link classes'''

class UserLink(object):
    '''The base class for user_links'''

    def __init__(self, device, reciprocal_id, group_number, data):
        self._root_device = device.root
        self._core = device.root.core
        self._address = reciprocal_id.upper()
        self._group = int(group_number)
        self._data_1 = data['data_1']
        self._data_2 = data['data_2']
        self._data_3 = data['data_3']
        self._uid = self._core.get_new_user_link_unique_id()

    @property
    def device(self):
        device = self._root_device.get_object_by_group_num(self.data_3)
        return device

    @property
    def controller_id(self):
        return self._address

    @property
    def group(self):
        return self._group

    @property
    def data(self):
        return {'data_1': self._data_1,
                'data_2': self._data_2,
                'data_3': self._data_3}
    @property
    def data_1(self):
        return self._data_1

    @property
    def data_2(self):
        return self._data_2

    @property
    def data_3(self):
        return self._data_3

    @property
    def controller_device(self):
        '''Returns the controller device of this link or None if it does not
        exist'''
        root = self._core.get_device_by_addr(self._address)
        ret = None
        if root is not None:
            ret = root.get_object_by_group_num(self._group)
        return ret

    @property
    def uid(self):
        '''An integer that is unique to all user_links in the core. The uid
        is not consistent across restarts.'''
        return self._uid

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
                    aldb_parsed['in_use'] is True):
                if (aldb_parsed['controller'] is True and
                        linked_addr == self.device.root.dev_addr_str):
                    ret = True
                elif(aldb_parsed['controller'] is False and
                     record_addr == self.device.root.dev_addr_str):
                    ret = True
        return ret

    def aldb_records_exist(self):
        ret = False
        attributes = {
            'in_use':  True,
            'responder': True,
            'group': self.group,
            'dev_addr_hi': self.controller_device.root.dev_addr_hi,
            'dev_addr_mid': self.controller_device.root.dev_addr_mid,
            'dev_addr_low': self.controller_device.root.dev_addr_low,
            'data_1': self.data_1,
            'data_2': self.data_2,
            'data_3': self.data_3
        }
        records = self.device.root.aldb.get_matching_records(attributes)
        if len(records) > 0:
            attributes = {
                'in_use':  True,
                'controller': True,
                'group': self.group,
                'dev_addr_hi': self.device.root.dev_addr_hi,
                'dev_addr_mid': self.device.root.dev_addr_mid,
                'dev_addr_low': self.device.root.dev_addr_low
            }
            records = self.controller_device.root.aldb.get_matching_records(attributes)
            if len(records) > 0:
                ret = True
        return ret
