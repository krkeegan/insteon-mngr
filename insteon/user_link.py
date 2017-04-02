'''The user_link classes'''

class UserLink(object):
    '''The base class for user_links'''

    def __init__(self, device, reciprocal_id, group_number, data, uid):
        self._root_device = device.root
        self._core = device.root.core
        self._address = reciprocal_id.upper()
        self._group = int(group_number)
        self._data_1 = data['data_1']
        self._data_2 = data['data_2']
        self._data_3 = data['data_3']
        self._uid = uid
        if uid is None:
            self._uid = self._core.get_new_user_link_unique_id()
        self._controller_key = None
        self._responder_key = None
        if 'controller_key' in data:
            self._controller_key = data['controller_key']
        if 'responder_key' in data:
            self._responder_key = data['responder_key']

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
                'data_3': self._data_3,
                'controller_key': self._controller_key,
                'responder_key': self._responder_key}
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

    @property
    def controller_key(self):
        return self._controller_key

    @property
    def responder_key(self):
        return self._responder_key

    def are_aldb_records_correct(self):
        ret = False
        responder = self.device.root.aldb.get_record(self._responder_key).parse_record()
        controller = self.controller_device.root.aldb.get_record(self._controller_key).parse_record()
        if (responder['in_use'] == True and
            responder['responder'] == True and
            responder['group'] == self.group and
            responder['dev_addr_hi'] == self.controller_device.root.dev_addr_hi and
            responder['dev_addr_mid'] == self.controller_device.root.dev_addr_mid and
            responder['dev_addr_low'] == self.controller_device.root.dev_addr_low and
            responder['data_1'] == self.data_1 and
            responder['data_2'] == self.data_2 and
            responder['data_3'] == self.data_3
            ):
            if (controller['in_use'] == True and
                controller['controller'] == True and
                controller['group'] == self.group and
                controller['dev_addr_hi'] == self.device.root.dev_addr_hi and
                controller['dev_addr_mid'] == self.device.root.dev_addr_mid and
                controller['dev_addr_low'] == self.device.root.dev_addr_low
                ):
                ret = True
        return ret
