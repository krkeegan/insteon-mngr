'''The user_link classes'''

from insteon import ID_STR_TO_BYTES

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
        self._link_sequence = None
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
    def dev_addr_hi(self):
        return ID_STR_TO_BYTES(self._address)[0]

    @property
    def dev_addr_mid(self):
        return ID_STR_TO_BYTES(self._address)[1]

    @property
    def dev_addr_low(self):
        return ID_STR_TO_BYTES(self._address)[2]

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

    @property
    def link_sequence(self):
        return self._link_sequence

    def are_aldb_records_correct(self):
        ret = False
        if (self._is_responder_correct() is True and
                self._is_controller_correct() is True):
            ret = True
        return ret

    def edit(self, controller, data):
        '''Edits the user link'''
        # TODO need to call some sort of aldb_write process
        if data['responder_id'] != self._root_device.dev_addr_str:
            device = self._core.get_device_by_addr(data['responder_id'])
            data['controller_key'] = self.controller_key
            device.add_user_link(controller, data, self.uid)
            self._root_device.delete_user_link(self.uid)
        else:
            self._data_1 = data['data_1']
            self._data_2 = data['data_2']
            self._data_3 = data['data_3']
        self.fix()

    def fix(self):
        '''Does whatever is necessary to get this link in the proper state
        returns nothing, but you can query the link itself or the link_sequence
        if set to get the status'''
        # TODO check if already active link sequence?
        ret = None
        if self._is_controller_correct() is False:
            if self._adoptable_controller_key() is not None:
                self._controller_key = self._adoptable_controller_key()
            else:
                ret = self.controller_device.root.send_handler.create_controller_link_sequence(self)
        if self._is_responder_correct() is False:
            if self._adoptable_responder_key() is not None:
                self._responder_key = self._adoptable_responder_key()
            else:
                if ret is None:
                    ret = self._root_device.send_handler.create_responder_link_sequence(self)
                else:
                    ret.success_callback = self._root_device.send_handler.create_responder_link_sequence(self).start
        if ret is not None:
            ret.start()
        self._link_sequence = ret

    def delete(self):
        '''Deletes this user link and wipes the associated links on the
        devices'''
        controller_sequence = None
        responder_sequence = None
        if self.controller_key is not None:
            controller_sequence = self.controller_device.root.send_handler.delete_record(key=self.controller_key)
        if self.responder_key is not None:
            responder_sequence = self._root_device.send_handler.delete_record(key=self.responder_key)
        if responder_sequence is not None and controller_sequence is not None:
            responder_sequence.success_callback = lambda: self._root_device.delete_user_link(self.uid)
            controller_sequence.success_callback = lambda: responder_sequence.start()
            controller_sequence.start()
        elif responder_sequence is not None:
            responder_sequence.success_callback = lambda: self._root_device.delete_user_link(self.uid)
            responder_sequence.start()
        elif controller_sequence is not None:
            controller_sequence.success_callback = lambda: self._root_device.delete_user_link(self.uid)
            controller_sequence.start()
        else:
            self._root_device.delete_user_link(self.uid)

    def _adoptable_responder_key(self):
        '''Looks for an existing undefined aldb entry that matches this link
        and returns that key if found'''
        ret = None
        attributes = {
            'in_use':  True,
            'responder': True,
            'group': self.group,
            'dev_addr_hi': self.dev_addr_hi,
            'dev_addr_mid': self.dev_addr_mid,
            'dev_addr_low': self.dev_addr_low,
            'data_1': self.data_1,
            'data_2': self.data_2,
            'data_3': self.data_3,
        }
        links = self.device.root.aldb.get_matching_records(attributes)
        if len(links) > 0:
            ret = links[0].key
        return ret

    def _adoptable_controller_key(self):
        '''Looks for an existing undefined aldb entry that matches this link
        and returns that key if found'''
        ret = None
        attributes = {
            'in_use':  True,
            'controller': True,
            'group': self.group,
            'dev_addr_hi': self.device.root.dev_addr_hi,
            'dev_addr_mid': self.device.root.dev_addr_mid,
            'dev_addr_low': self.device.root.dev_addr_low
            # Not checking data_1-3 at the moment
        }
        links = self.controller_device.root.aldb.get_matching_records(attributes)
        if len(links) > 0:
            ret = links[0].key
        return ret

    def _is_responder_correct(self):
        ret = False
        if (self._responder_key is not None):
            responder = self.device.root.aldb.get_record(self._responder_key).parse_record()
            if (responder['in_use'] == True and
                    responder['responder'] == True and
                    responder['group'] == self.group and
                    responder['dev_addr_hi'] == self.dev_addr_hi and
                    responder['dev_addr_mid'] == self.dev_addr_mid and
                    responder['dev_addr_low'] == self.dev_addr_low and
                    responder['data_1'] == self.data_1 and
                    responder['data_2'] == self.data_2 and
                    responder['data_3'] == self.data_3
               ):
                ret = True
        return ret

    def _is_controller_correct(self):
        ret = False
        if (self._controller_key is not None):
            controller = self.controller_device.root.aldb.get_record(self._controller_key).parse_record()
            if (controller['in_use'] == True and
                    controller['controller'] == True and
                    controller['group'] == self.group and
                    controller['dev_addr_hi'] == self.device.root.dev_addr_hi and
                    controller['dev_addr_mid'] == self.device.root.dev_addr_mid and
                    controller['dev_addr_low'] == self.device.root.dev_addr_low
               ):
                ret = True
        return ret
