from .helpers import BYTE_TO_HEX, BYTE_TO_ID
from .trigger import Trigger


class ALDB(object):

    def __init__(self, parent):
        self._parent = parent
        self.aldb = {}

    def edit_record(self, position, record):
        self.aldb[position] = record

    def delete_record(self, position):
        del(self.aldb[position])

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
        for position, record in self.aldb.items():
            parsed_record = self.parse_record(position)
            ret.append(position)
            for attribute, value in attributes.items():
                if parsed_record[attribute] != value:
                    ret.remove(position)
                    break
        return ret

    def parse_record(self, position):
        bytes = self.aldb[position]
        parsed = {
            'record_flag': bytes[0],
            'in_use':  bytes[0] & 0b10000000,
            'controller':  bytes[0] & 0b01000000,
            'responder': ~bytes[0] & 0b01000000,
            'highwater': ~bytes[0] & 0b00000010,
            'group': bytes[1],
            'dev_addr_hi': bytes[2],
            'dev_addr_mid': bytes[3],
            'dev_addr_low': bytes[4],
            'data_1': bytes[5],
            'data_2': bytes[6],
            'data_3': bytes[7],
        }
        for attr in ('in_use', 'controller', 'responder', 'highwater'):
            if parsed[attr]:
                parsed[attr] = True
            else:
                parsed[attr] = False
        return parsed

    def get_linked_obj(self, position):
        parsed_record = self.parse_record(position)
        high = parsed_record['dev_addr_hi']
        mid = parsed_record['dev_addr_mid']
        low = parsed_record['dev_addr_low']
        return self._parent.plm.get_device_by_addr(BYTE_TO_ID(high, mid, low))

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
