'''The base ALDB Objects'''
from insteon.base_objects import BYTE_TO_HEX, BYTE_TO_ID


class ALDB(object):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, parent):
        self._parent = parent
        self.aldb = {}

    def delete_position(self, position):
        del self.aldb[position]

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
        for position in self.aldb:
            record = self.aldb[position]
            parsed_record = record.parse_record()
            ret.append(record)
            for attribute, value in attributes.items():
                if parsed_record[attribute] != value:
                    ret.remove(record)
                    break
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
        self._core = self._database._parent.core
        self._link_sequence = None

    @property
    def device(self):
        '''Returns the device to which this record belongs'''
        group = self.parse_record()['group']
        if self.is_controller() is False:
            group = self.parse_record()['data_3']
        return self._database._parent.get_object_by_group_num(group)

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
        ret = self._database._parent.send_handler.delete_record(key=self.key)
        ret.start()
        self._link_sequence = ret

    def delete_record(self):
        '''Removes the record from the cache only'''
        del self._database.aldb[self.key]

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
        '''If this is a responder link it returns the controller object.
        If this is a controller link, it returns the root of the responder
        object, as multiple group responders could exist.'''
        device = None
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        root = self._core.get_device_by_addr(BYTE_TO_ID(high, mid, low))
        group = 0x01
        # TODO we should really consider if multiple responders on a single
        # device is realistic. And secondly, how we should handle such in this
        # case.  Returning the root seems like it will work, until it doesn't
        # and then finding this bug will be tedious
        if self.is_controller is False:
            group = parsed_record['group']
        if root is not None:
            device = root.get_object_by_group_num(group)
        return device

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
        ret = False
        if self.is_controller():
            user_links = self._core.get_user_links_for_this_controller(self.device)
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

    def get_linked_device_str(self):
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        string = BYTE_TO_ID(high, mid, low)
        return string

    def get_reciprocal_records(self):
        linked_root = None
        if self.linked_device is not None:
            linked_root = self.linked_device.root
        parsed = self.parse_record()
        controller = True
        records = []
        if parsed['controller']:
            controller = False
        if linked_root is not None:
            search = {
                'controller': controller,
                'group': parsed['group'],
                'dev_addr_hi': self._database._parent.dev_addr_hi,
                'dev_addr_mid': self._database._parent.dev_addr_mid,
                'dev_addr_low': self._database._parent.dev_addr_low,
                'in_use': True
            }
            records = linked_root.aldb.get_matching_records(search)
        return records

    def edit_record(self, record):
        self.raw = record

    def edit_record_byte(self, byte_pos, byte):
        self.raw[byte_pos] = byte
