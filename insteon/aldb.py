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
        '''Returns an array of positions of each records that matches ALL
        attributes'''
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
        for key in sorted(records, reverse=True):
            if self.aldb[key].is_empty_aldb():
                ret = key
                break
        return ret


class ALDBRecord(object):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, database, raw=bytearray(8)):
        self._raw = raw
        self._database = database

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

    def delete_record(self):
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

    def get_linked_root_obj(self):
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        plm = self._database._parent.plm
        return plm.get_device_by_addr(BYTE_TO_ID(high, mid, low))

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

    def get_linked_device_str(self):
        parsed_record = self.parse_record()
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        string = BYTE_TO_ID(high, mid, low)
        return string

    def get_reciprocal_records(self):
        linked_root = self.get_linked_root_obj()
        parsed = self.parse_record()
        controller = False
        if parsed['controller']:
            controller = True
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

    def get_group_object(self):
        ret = self._database._parent
        if self.parse_record()['responder']:
            ret = self._database._parent.get_object_by_group_num(
                self.parse_record()['data_3']
            )
        return ret


    def edit_record(self, record):
        self.raw = record

    def edit_record_byte(self, byte_pos, byte):
        self.raw[byte_pos] = byte
