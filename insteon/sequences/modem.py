from insteon.trigger import PLMTrigger
from insteon.sequences.common import WriteALDBRecord


class WriteALDBRecordModem(WriteALDBRecord):
    def _perform_write(self):
        super()._perform_write()
        if self.in_use is True:
            self.data1 = self.linked_device.root.dev_cat
            self.data2 = self.linked_device.root.sub_cat
            self.data3 = self.linked_device.root.firmware
        msg = self._device.root.send_handler.create_message('all_link_manage_rec')
        msg_attributes = self._compiled_record()
        msg.insert_bytes_into_raw(msg_attributes)
        trigger_attributes = {
            'plm_cmd': 0x6F,
            'ctrl_code': msg_attributes['ctrl_code'],
            'link_flags': msg_attributes['link_flags'],
            'group': msg_attributes['group'],
            'dev_addr_hi': msg_attributes['dev_addr_hi'],
            'dev_addr_mid': msg_attributes['dev_addr_mid'],
            'dev_addr_low': msg_attributes['dev_addr_low'],
            'data_1': msg_attributes['data_1'],
            'data_2': msg_attributes['data_2'],
            'data_3': msg_attributes['data_3']
        }
        trigger = PLMTrigger(plm=self._device.root,
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._save_record()
        trigger.name = self._device.root.dev_addr_str + 'write_aldb'
        trigger.queue()
        self._device.root.queue_device_msg(msg)

    def _ctrl_code(self, search_bytes):
        records = self._device.root.aldb.get_matching_records(search_bytes)
        ctrl_code = 0x20
        if (len(records) == 0 and self.controller is True):
            ctrl_code = 0x40
        if (len(records) == 0 and self.controller is False):
            ctrl_code = 0x41
        return ctrl_code

    def _compiled_record(self):
        ret = super()._compiled_record()
        del ret['msb']
        del ret['lsb']
        if not self.in_use:
            record = self._device.root.aldb.get_record(self.key)
            record_parsed = record.parse_record()
            ret['link_flags'] = record_parsed['link_flags']
            ret['group'] = record_parsed['group']
            ret['dev_addr_hi'] = record_parsed['dev_addr_hi']
            ret['dev_addr_mid'] = record_parsed['dev_addr_mid']
            ret['dev_addr_low'] = record_parsed['dev_addr_low']
            ret['ctrl_code'] = 0x80
        else:
            search_bytes = {
                'link_flags': ret['link_flags'],
                'group': ret['group'],
                'dev_addr_hi': ret['dev_addr_hi'],
                'dev_addr_mid': ret['dev_addr_mid'],
                'dev_addr_low': ret['dev_addr_low']
            }
            ret['ctrl_code'] = self._ctrl_code(search_bytes)
        return ret

    def _save_record(self):
        aldb_entry = bytearray([
            self._compiled_record()['link_flags'],
            self._compiled_record()['group'],
            self._compiled_record()['dev_addr_hi'],
            self._compiled_record()['dev_addr_mid'],
            self._compiled_record()['dev_addr_low'],
            self._compiled_record()['data_1'],
            self._compiled_record()['data_2'],
            self._compiled_record()['data_3']
        ])
        record = self._device.root.aldb.get_record(self.key)
        record.edit_record(aldb_entry)
        self.on_success()

    def _write_failure(self):
        self.on_failure()

    def start(self):
        '''Starts the sequence to write the aldb record'''
        if self.linked_device is None and self.in_use:
            print('error no linked_device defined')
        else:
            self._perform_write()
