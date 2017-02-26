'''The base ALDB Objects'''
from insteon.base_objects import BYTE_TO_HEX, BYTE_TO_ID


class ALDB(object):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, parent):
        self._parent = parent
        self.aldb = {}

    def edit_record(self, position, record):
        self.aldb[position] = record

    def delete_record(self, position):
        del self.aldb[position]

    def get_record(self, position):
        return self.aldb[position]

    def get_all_records(self):
        return self.aldb.copy()

    def get_all_records_str(self):
        ret = {}
        for key, value in self.aldb.items():
            ret[key] = BYTE_TO_HEX(value)
        return ret

    def load_aldb_records(self, records):
        for key, record in records.items():
            self.edit_record(key, bytearray.fromhex(record))

    def clear_all_records(self):
        self.aldb = {}

    def edit_record_byte(self, aldb_pos, byte_pos, byte):
        self.aldb[aldb_pos][byte_pos] = byte

    def get_matching_records(self, attributes):
        '''Returns an array of positions of each records that matches ALL
        attributes'''
        ret = []
        for position in self.aldb:
            parsed_record = self.parse_record(position)
            ret.append(position)
            for attribute, value in attributes.items():
                if parsed_record[attribute] != value:
                    ret.remove(position)
                    break
        return ret

    def parse_record(self, position):
        record_bytes = self.aldb[position]
        parsed = {
            'link_flags': record_bytes[0],
            'in_use':  record_bytes[0] & 0b10000000,
            'controller':  record_bytes[0] & 0b01000000,
            'responder': ~record_bytes[0] & 0b01000000,
            'highwater': ~record_bytes[0] & 0b00000010,
            'group': record_bytes[1],
            'dev_addr_hi': record_bytes[2],
            'dev_addr_mid': record_bytes[3],
            'dev_addr_low': record_bytes[4],
            'data_1': record_bytes[5],
            'data_2': record_bytes[6],
            'data_3': record_bytes[7],
        }
        for attr in ('in_use', 'controller', 'responder', 'highwater'):
            parsed[attr] = bool(parsed[attr])
        return parsed

    def get_linked_root_obj(self, position):
        parsed_record = self.parse_record(position)
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        return self._parent.plm.get_device_by_addr(BYTE_TO_ID(high, mid, low))

    def get_responder_and_level(self, position):
        # This function seems rather hacky and specific, there must be a
        # more elegant way to do this
        # should each ALDB record be an object?  Would make a lot of these
        # things a lot better, can just pass the record object and make Calls
        # on the object
        ret = []
        linked_root = self.get_linked_root_obj(position)
        parsed_root = self.parse_record(position)
        if linked_root is not None and parsed_root['controller']:
            records = linked_root.aldb.get_matching_records({
                'controller': False,
                'group': parsed_root['group'],
                'dev_addr_hi': self._parent.dev_addr_hi,
                'dev_addr_mid': self._parent.dev_addr_mid,
                'dev_addr_low': self._parent.dev_addr_low,
                'in_use': True
            })
            for record in records:
                parsed_record = linked_root.aldb.parse_record(record)
                obj = linked_root.get_object_by_group_num(parsed_record['data_3'])
                if obj is not None:
                    ret.append([obj, parsed_record['data_1']])
        return ret

    def is_last_aldb(self, key):
        ret = True
        if self.get_record(key)[0] & 0b00000010:
            ret = False
        return ret

    def is_empty_aldb(self, key):
        ret = True
        if self.get_record(key)[0] & 0b10000000:
            ret = False
        return ret

    def print_records(self):
        records = self.get_all_records()
        for key in sorted(records):
            print(key, ":", BYTE_TO_HEX(records[key]))

    def get_first_empty_addr(self):
        records = self.get_all_records()
        ret = None
        for key in sorted(records, reverse=True):
            if self.is_empty_aldb(key):
                ret = key
                break
        return ret

    def get_linked_device_str(self, position):
        parsed_record = self.parse_record(position)
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        string = BYTE_TO_ID(high, mid, low)
        return string
