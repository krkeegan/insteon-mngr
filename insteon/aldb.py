from .helpers import BYTE_TO_HEX, BYTE_TO_ID
from .trigger import Trigger


class ALDB(object):

    def __init__(self, parent):
        self._parent = parent
        self._aldb = {}

    def edit_record(self, position, record):
        self._aldb[position] = record

    def delete_record(self, position):
        del(self._aldb[position])

    def get_record(self, position):
        return self._aldb[position]

    def get_all_records(self):
        return self._aldb.copy()

    def get_all_records_str(self):
        ret = {}
        for key, value in self._aldb.items():
            ret[key] = BYTE_TO_HEX(value)
        return ret

    def load_aldb_records(self, records):
        for key, record in records.items():
            self.edit_record(key, bytearray.fromhex(record))

    def clear_all_records(self):
        self._aldb = {}

    def edit_record_byte(self, aldb_pos, byte_pos, byte):
        self._aldb[aldb_pos][byte_pos] = byte

    def get_matching_records(self, attributes):
        '''Returns an array of positions of each records that matches ALL
        attributes'''
        ret = []
        for position, record in self._aldb.items():
            parsed_record = self.parse_record(position)
            ret.append(position)
            for attribute, value in attributes.items():
                if parsed_record[attribute] != value:
                    ret.remove(position)
                    break
        return ret

    def parse_record(self, position):
        bytes = self._aldb[position]
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


class Device_ALDB(ALDB):

    def __init__(self, parent):
        super().__init__(parent)

    def _get_aldb_key(self, msb, lsb):
        offset = 7 - (lsb % 8)
        highest_byte = lsb + offset
        key = bytes([msb, highest_byte])
        return BYTE_TO_HEX(key)

    def query_aldb(self):
        self.clear_all_records()
        if self._parent.attribute('engine_version') == 0:
            self.i1_start_aldb_entry_query(0x0F, 0xF8)
        else:
            dev_bytes = {'msb': 0x00, 'lsb': 0x00}
            self._parent.send_command('read_aldb',
                                      'query_aldb',
                                      dev_bytes=dev_bytes)
            # It would be nice to link the trigger to the msb and lsb, but we
            # don't technically have that yet at this point
            trigger_attributes = {
                'plm_cmd': 0x51,
                'cmd_1': 0x2F,
                'from_addr_hi': self._parent.dev_addr_hi,
                'from_addr_mid': self._parent.dev_addr_mid,
                'from_addr_low': self._parent.dev_addr_low,
            }
            trigger = Trigger(trigger_attributes)
            trigger.trigger_function = lambda: self.i2_next_aldb()
            trigger_name = self._parent.dev_addr_str + 'query_aldb'
            self._parent.plm._trigger_mngr.add_trigger(trigger_name, trigger)

    def i2_next_aldb(self):
        # TODO parse by real names on incomming
        msb = self._parent.last_rcvd_msg.get_byte_by_name('usr_3')
        lsb = self._parent.last_rcvd_msg.get_byte_by_name('usr_4')
        if self.is_last_aldb(self._get_aldb_key(msb, lsb)):
            self._parent.remove_state_machine('query_aldb')
            records = self.get_all_records()
            for key in sorted(records):
                print(key, ":", BYTE_TO_HEX(records[key]))
            self._parent.send_command('light_status_request', 'set_aldb_delta')
        else:
            if lsb == 0x07:
                msb -= 1
                lsb = 0xFF
            else:
                lsb -= 8
            dev_bytes = {'msb': msb, 'lsb': lsb}
            self._parent.send_command('read_aldb',
                                      'query_aldb',
                                      dev_bytes=dev_bytes)
            # Set Trigger
            trigger_attributes = {
                'plm_cmd': 0x51,
                'cmd_1': 0x2F,
                'usr_3': msb,
                'usr_4': lsb,
                'from_addr_hi': self._parent.dev_addr_hi,
                'from_addr_mid': self._parent.dev_addr_mid,
                'from_addr_low': self._parent.dev_addr_low,
            }
            trigger = Trigger(trigger_attributes)
            trigger.trigger_function = lambda: self.i2_next_aldb()
            trigger_name = self._parent.dev_addr_str + 'query_aldb'
            self._parent.plm._trigger_mngr.add_trigger(trigger_name, trigger)

    def i1_start_aldb_entry_query(self, msb, lsb):
        message = self._parent.create_message('set_address_msb')
        message._insert_bytes_into_raw({'msb': msb})
        message.insteon_msg.device_success_callback = \
            lambda: \
            self.peek_aldb(lsb)
        self._parent._queue_device_msg(message, 'query_aldb')

    def peek_aldb(self, lsb):
        message = self._parent.create_message('peek_one_byte')
        message._insert_bytes_into_raw({'lsb': lsb})
        self._parent._queue_device_msg(message, 'query_aldb')

    def create_responder(self, controller, d1, d2, d3):
                # Device Responder
                # D1 On Level D2 Ramp Rate D3 Group of responding device i1 00
                # i2 01
        pass

    def create_controller(responder):
                # Device controller
                # D1 03 Hops?? D2 00 D3 Group 01 of responding device??
        pass

    def _write_link(self, linked_obj, is_controller):
        if self._parent.attribute('engine_version') == 2:
            pass  # run i2cs commands
        else:
            pass  # run i1 commands
        pass


class PLM_ALDB(ALDB):

    def add_record(self, aldb):
        position = str(len(self._aldb) + 1)
        position = position.zfill(4)
        self._aldb[position] = aldb

    def have_aldb_cache(self):
        # TODO This will return false for an empty aldb as well, do we care?
        ret = True
        if len(self._aldb) == 0:
            ret = False
        return ret

    def query_aldb(self):
        '''Queries the PLM for a list of the link records saved on
        the PLM and stores them in the cache'''
        self.clear_all_records()
        self._parent.send_command('all_link_first_rec', 'query_aldb')

    def create_responder(self, controller, *args):
        self._write_link(controller, is_plm_controller=False)

    def create_controller(self, controller, *args):
        self._write_link(controller, is_plm_controller=True)

    def _write_link(self, linked_obj, is_plm_controller):
        group = linked_obj.group_number
        if is_plm_controller:
            group = self._parent.group_number
        link_bytes = {
            'controller': True if is_plm_controller else False,
            'responder': False if is_plm_controller else True,
            'group': group,
            'dev_addr_hi': linked_obj.dev_addr_hi,
            'dev_addr_mid': linked_obj.dev_addr_mid,
            'dev_addr_low': linked_obj.dev_addr_low,
        }
        del link_bytes['controller']
        del link_bytes['responder']
        records = self.get_matching_records(link_bytes)
        link_flags = 0xE2 if is_plm_controller else 0xA2
        ctrl_code = 0x20
        if (len(records) == 0):
            ctrl_code = 0x40 if is_plm_controller else 0x41
        link_bytes.update({
            'ctrl_code': ctrl_code,
            'link_flags': link_flags,
            'data_1': linked_obj.dev_cat,
            'data_2': linked_obj.sub_cat,
            'data_3': linked_obj.firmware
        })
        self._parent.send_command('all_link_manage_rec', '', link_bytes)
