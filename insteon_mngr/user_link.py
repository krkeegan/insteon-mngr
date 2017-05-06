'''The user_link classes'''

from insteon_mngr import ID_STR_TO_BYTES
from insteon_mngr.sequences import DeleteLinkPair

class UserLink(object):
    '''The base class for user_links'''

    def __init__(self, device, reciprocal_id, group_number, data, uid):
        self._device = device
        self._core = device.core
        self._address = reciprocal_id.upper()
        self._group_number = int(group_number)
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
    def responder_device(self):
        return self._device

    @property
    def responder_group(self):
        return self._device.get_object_by_group_num(self._data_3)

    @property
    def controller_id(self):
        return self._address

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
        return self._core.get_device_by_addr(self._address)

    @property
    def controller_group(self):
        ret = None
        root = self.controller_device
        if root is not None:
            ret = root.get_object_by_group_num(self._group_number)
        return ret

    @property
    def controller_group_number(self):
        return self._group_number

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

    def set_controller_key(self, key):
        self._controller_key = key

    def set_responder_key(self, key):
        self._responder_key = key

    def edit(self, controller, data):
        '''Edits the user link'''
        if data['responder_id'] != self._device.dev_addr_str:
            device = self._core.get_device_by_addr(data['responder_id'])
            data['controller_key'] = self.controller_key
            device.add_user_link(controller, data, self.uid)
            self._device.delete_user_link(self.uid)
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
        controller_sequence = None
        responder_sequence = None
        if self._is_controller_correct() is False:
            if self._adoptable_controller_key() is not None:
                self._controller_key = self._adoptable_controller_key()
            else:
                controller_sequence = self.controller_group.create_controller_link_sequence(self)
        if self._is_responder_correct() is False:
            if self._adoptable_responder_key() is not None:
                self._responder_key = self._adoptable_responder_key()
            else:
                responder_sequence = self.responder_group.create_responder_link_sequence(self)
        if responder_sequence is not None and controller_sequence is not None:
            responder_sequence.success_callback = lambda: (
                self.set_controller_key(controller_sequence.key),
                self.set_responder_key(responder_sequence.key),
                )
            controller_sequence.success_callback = lambda: responder_sequence.start()
            ret = controller_sequence
            controller_sequence.start()
        elif responder_sequence is not None:
            responder_sequence.success_callback = lambda: self.set_responder_key(responder_sequence.key)
            ret = responder_sequence
            responder_sequence.start()
        elif controller_sequence is not None:
            controller_sequence.success_callback = lambda: self.set_controller_key(controller_sequence.key)
            ret = controller_sequence
            controller_sequence.start()
        self._link_sequence = ret

    def delete(self):
        '''Deletes this user link and wipes the associated links on the
        devices'''
        delete_sequence = DeleteLinkPair()
        delete_sequence.set_controller_device_with_key(self.controller_device,
                                                       self.controller_key)
        delete_sequence.set_responder_device_with_key(self._device,
                                                      self.responder_key)
        delete_sequence.success_callback = lambda: self._device.delete_user_link(self.uid)
        delete_sequence.start()
        self._link_sequence = delete_sequence

    def status(self):
        '''Returns a string representing the status of the user_link'''
        status = 'Broken'
        if self.are_aldb_records_correct() is True:
            status = 'Good'
        elif self.link_sequence is not None:
            if self.link_sequence.is_complete is False:
                status = 'Working'
            elif self.link_sequence.is_success is False:
                status = 'Failed'
        return status

    def json(self):
        '''Returns a dict to be used as a json reprentation of the user_link'''
        ret = {}
        ret[self.uid] = {
            'responder_id': self.responder_device.dev_addr_str,
            'responder_name': self.responder_group.name,
            'responder_group': self.data_3,
            'responder_key': self.responder_key,
            'controller_key': self.controller_key,
            'data_1': self.data_1,
            'data_2': self.data_2,
            'data_3': self.data_3,
            'status': self.status()
        }
        return ret

    def _adoptable_responder_key(self):
        '''Looks for an existing undefined aldb entry that matches this link
        and returns that key if found'''
        ret = None
        attributes = {
            'in_use':  True,
            'responder': True,
            'group': self._group_number,
            'dev_addr_hi': self.dev_addr_hi,
            'dev_addr_mid': self.dev_addr_mid,
            'dev_addr_low': self.dev_addr_low,
            'data_1': self.data_1,
            'data_2': self.data_2,
            'data_3': self.data_3,
        }
        links = self._device.aldb.get_matching_records(attributes)
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
            'group': self._group_number,
            'dev_addr_hi': self._device.dev_addr_hi,
            'dev_addr_mid': self._device.dev_addr_mid,
            'dev_addr_low': self._device.dev_addr_low
            # Not checking data_1-3 at the moment
        }
        links = self.controller_device.root.aldb.get_matching_records(attributes)
        if len(links) > 0:
            ret = links[0].key
        return ret

    def _is_responder_correct(self):
        ret = False
        if (self._responder_key is not None):
            responder = self._device.aldb.get_record(self._responder_key).parse_record()
            if (responder['in_use'] == True and
                    responder['responder'] == True and
                    responder['group'] == self._group_number and
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
                    controller['group'] == self._group_number and
                    controller['dev_addr_hi'] == self._device.dev_addr_hi and
                    controller['dev_addr_mid'] == self._device.dev_addr_mid and
                    controller['dev_addr_low'] == self._device.dev_addr_low
               ):
                ret = True
        return ret
