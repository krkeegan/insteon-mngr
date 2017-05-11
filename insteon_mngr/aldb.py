'''The base ALDB Objects'''
from insteon_mngr import BYTE_TO_HEX, BYTE_TO_ID


class ALDB(object):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, device):
        self._device = device
        self.aldb = {}

    @property
    def core(self):
        return self._device.core

    @property
    def device(self):
        return self._device

    def get_record(self, position):
        if position not in self.aldb:
            self.aldb[position] = ALDBRecord(self)
        return self.aldb[position]

    def get_all_records(self):
        ret = {}
        for key, record in self.aldb.items():
            ret[key] = record.raw
        return ret

    def get_all_records_str(self):
        ret = {}
        for key, record in self.aldb.items():
            ret[key] = BYTE_TO_HEX(record.raw)
        return ret

    def load_aldb_records(self, records):
        for key, record in records.items():
            self.aldb[key] = ALDBRecord(self, bytearray.fromhex(record))

    def clear_all_records(self):
        self.aldb = {}

    def get_matching_records(self, attributes):
        '''Returns an array of records that matches ALL attributes'''
        ret = []
        for record in self.aldb.values():
            parsed_record = record.parse_record()
            for attribute, value in attributes.items():
                if parsed_record[attribute] != value:
                    break
            else:
                ret.append(record)
        return ret

    def print_records(self):
        records = self.get_all_records()
        for key in sorted(records):
            print(key, ":", BYTE_TO_HEX(records[key]))

    def get_first_empty_addr(self):
        records = self.get_all_records()
        ret = None
        lowest = None
        for key in sorted(records, reverse=True):
            lowest = key
            if self.aldb[key].is_empty_aldb():
                ret = key
                break
        if ret is None:
            msb = int(lowest[0:2], 16)
            lsb = int(lowest[2:4], 16)
            if lsb >= 8:
                lsb = lsb - 8
            else:
                msb = msb - 1
            ret = ('{:02x}'.format(msb, 'x').upper() +
                   '{:02x}'.format(lsb, 'x').upper())
        return ret


class ALDBRecord(object):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, database, raw=bytearray(8)):
        self._raw = raw
        self._database = database
        self._core = self._database.core
        self._device = self._database.device
        self._link_sequence = None

    @property
    def device(self):
        '''Returns the device to which this record belongs'''
        return self._device

    @property
    def group_obj(self):
        '''Returns the group object to which this record belongs'''
        ret = None
        parsed_record = self.parse_record()
        if self.is_controller():
            ret = self.device.get_object_by_group_num(parsed_record['group'])
        else:
            # Be careful, relying on data_3 as the responder group is something
            # divined from practical use, not stated in the spec
            ret = self.device.get_object_by_group_num(parsed_record['data_3'])
        return ret

    @property
    def key(self):
        ret = None
        for key, record in self._database.aldb.items():
            if record == self:
                ret = key
                break
        return ret

    @property
    def raw(self):
        return self._raw

    @raw.setter
    def raw(self, value):
        self._raw = value

    @property
    def link_sequence(self):
        return self._link_sequence

    @link_sequence.setter
    def link_sequence(self, sequence):
        self._link_sequence = sequence

    def delete(self):
        '''Removes the record from the device and the cache'''
        ret = self._database.device.send_handler.delete_record(key=self.key)
        ret.start()
        self._link_sequence = ret

    def parse_record(self):
        parsed = {
            'link_flags': self.raw[0],
            'in_use':  self.raw[0] & 0b10000000,
            'controller':  self.raw[0] & 0b01000000,
            'responder': ~self.raw[0] & 0b01000000,
            'highwater': ~self.raw[0] & 0b00000010,
            'group': self.raw[1],
            'dev_addr_hi': self.raw[2],
            'dev_addr_mid': self.raw[3],
            'dev_addr_low': self.raw[4],
            'data_1': self.raw[5],
            'data_2': self.raw[6],
            'data_3': self.raw[7],
        }
        for attr in ('in_use', 'controller', 'responder', 'highwater'):
            parsed[attr] = bool(parsed[attr])
        return parsed

    @property
    def linked_device(self):
        '''Returns the device linked to this entry which will be either the
        controller or responder device.'''
        device = None
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        device = self._core.get_device_by_addr(BYTE_TO_ID(high, mid, low))
        return device

    @property
    def linked_group(self):
        '''Returns the reciprocal group linked to this entry.'''
        device = self.linked_device
        group = None
        if device is not None:
            if self.is_controller():
                records = self.get_reciprocal_records()
                if len(records) > 0:
                    group = records[0].group_obj
            else:
                parsed_record = self.parse_record()
                group = device.get_object_by_group_num(parsed_record['group'])
        return group

    def is_last_aldb(self):
        ret = True
        if self.raw[0] & 0b00000010:
            ret = False
        return ret

    def is_empty_aldb(self):
        ret = True
        if self.raw[0] & 0b10000000:
            ret = False
        return ret

    def is_controller(self):
        ret = False
        if self.parse_record()['controller'] is True:
            ret = True
        return ret

    def is_a_defined_link(self):
        '''Returns True if link key of this link is associated with a defined
        user_link'''
        ret = False
        if self.is_controller():
            user_links = self._core.get_user_links_for_this_controller(self.group_obj)
            for user_link in user_links.values():
                if user_link.controller_key == self.key:
                    ret = True
                    break
        else:
            user_links = self.device.root.get_all_user_links()
            for user_link in user_links.values():
                if user_link.responder_key == self.key:
                    ret = True
                    break
        return ret

    def get_defined_link(self):
        '''Returns the user link associated with the link key or None if doesnt
        exist'''
        ret = None
        if self.is_controller():
            user_links = self._core.get_user_links_for_this_controller(self.group_obj)
            for user_link in user_links.values():
                if user_link.controller_key == self.key:
                    ret = user_link
                    break
        else:
            user_links = self.device.root.get_all_user_links()
            for user_link in user_links.values():
                if user_link.responder_key == self.key:
                    ret = user_link
                    break
        return ret

    def status(self):
        '''Returns the status of the link as a string'''
        ret = ''
        user_link = self.get_defined_link()
        if self.is_empty_aldb():
            ret = 'emtpy'
        elif self._is_i2_modem_link():
            ret = 'i2_modem_link'
        elif user_link is not None:
            if user_link.are_aldb_records_correct():
                ret = 'good'
            else:
                ret = 'broken'
        elif self.linked_device is None:
            ret = 'unknown'
        elif self.group_obj is None:
            ret = 'bad_group'
        elif self.linked_group is None:
            ret = 'bad_linked_group'
        else:
            ret = 'undefined'
        return ret

    def _is_modem_notify_link(str):
        # this is for device links, not sure how to handle modem links
        # perhaps all responder links on modem if group exists
        pass
        # if is the group modem_link_key
        # if record matches expected
        # then modem_link_good
        # else modem_link_bad


    def _is_i2_modem_link(self):
        # this is for device links, not sure how to handle modem links
        # perhaps all controller links from a specific group on modem if
        # device exists
        ret = False
        parsed = self.parse_record()
        if (parsed['responder'] is True and
                parsed['group'] == 0x00 and
                parsed['dev_addr_hi'] == self._device.plm.dev_addr_hi and
                parsed['dev_addr_mid'] == self._device.plm.dev_addr_mid and
                parsed['dev_addr_low'] == self._device.plm.dev_addr_low):
            ret = True
        return ret

    def get_linked_device_str(self):
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        string = BYTE_TO_ID(high, mid, low)
        return string

    def get_reciprocal_records(self):
        linked_root = self.linked_device
        parsed = self.parse_record()
        controller = True
        records = []
        if parsed['controller']:
            controller = False
        if linked_root is not None:
            search = {
                'controller': controller,
                'group': parsed['group'],
                'dev_addr_hi': self._database.device.dev_addr_hi,
                'dev_addr_mid': self._database.device.dev_addr_mid,
                'dev_addr_low': self._database.device.dev_addr_low,
                'in_use': True
            }
            records = linked_root.aldb.get_matching_records(search)
        return records

    def edit_record(self, record):
        self.raw = record

    def edit_record_byte(self, byte_pos, byte):
        self.raw[byte_pos] = byte

    def json(self):
        '''Returns a dict to be used as a json reprentation of the link'''
        records = self.get_reciprocal_records()
        parsed_record = self.parse_record()
        ret = {'responder_key': None,
               'controller_key': None,
               'responder_id': None,
               'responder_name': None,
               'responder_group': None,
               'data_1': None,
               'data_2': None,
               'data_3': None,
               'status': self.status(),
               'controller_raw': None,
               'responder_raw': None,
               'controller_group': parsed_record['group']}
        if self.is_controller():
            ret['responder_id'] = self.get_linked_device_str()
            ret['controller_key'] = self.key
            ret['controller_raw'] = BYTE_TO_HEX(self.raw)
            if len(records) > 0:
                ret['responder_key'] = records[0].key
                ret['responder_raw'] = BYTE_TO_HEX(records[0].raw)
                parsed_record2 = records[0].parse_record()
                ret['data_1'] = parsed_record2['data_1']
                ret['data_2'] = parsed_record2['data_2']
                ret['data_3'] = parsed_record2['data_3']
            if self.linked_group is not None:
                ret['responder_name'] = self.linked_group.name
                ret['responder_group'] = self.linked_group.group_number
        else:
            ret['responder_id'] = self.device.dev_addr_str
            ret['responder_key'] = self.key
            ret['data_1'] = parsed_record['data_1']
            ret['data_2'] = parsed_record['data_2']
            ret['data_3'] = parsed_record['data_3']
            ret['responder_raw'] = BYTE_TO_HEX(self.raw)
            if len(records) > 0:
                ret['controller_key'] = records[0].key
                ret['controller_raw'] = BYTE_TO_HEX(records[0].raw)
            if self.group_obj is not None:
                ret['responder_name'] = self.group_obj.name
                ret['responder_group'] = self.group_obj.group_number

        # Define the UID for the Link
        rkey = '----'
        ckey = '----'
        if ret['responder_key'] is not None:
            rkey = ret['responder_key']
        if ret['controller_key'] is not None:
            ckey = ret['controller_key']
        return {ret['responder_id'] + rkey + ckey: ret}
