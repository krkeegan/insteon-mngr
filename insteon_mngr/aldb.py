'''The base ALDB Objects'''
from insteon_mngr import BYTE_TO_HEX, BYTE_TO_ID


class ALDB(dict):
    '''The base ALDB class which is inherited by both the Device and PLM
    ALDB classes'''
    def __init__(self, device):
        self._device = device
        self.aldb = {}

    @property
    def device(self):
        return self._device

    def __getitem__(self, key):
        if key not in self:
            self[key] = ALDBRecord(self)
        return self[key]

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

    def __str__(self):
        ret = ''
        for key in sorted(self):
            ret = ret + key + " : " + BYTE_TO_HEX(self[key]) + "\n"
        return ret

    def get_first_empty_addr(self):
        ret = None
        lowest = None
        for key in sorted(self, reverse=True):
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
        ret = []
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
            for record in linked_root.aldb:
                if record.matches(search):
                    ret.append(record)
        return ret

    def edit_record(self, record):
        self.raw = record

    def edit_record_byte(self, byte_pos, byte):
        self.raw[byte_pos] = byte

    def matches(self, attributes):
        '''Returns true if passed attributes match ALL of record'''
        ret = True
        parsed_record = self.parse_record()
        for attribute, value in attributes.items():
            if parsed_record[attribute] != value:
                ret = False
                break
        return ret
