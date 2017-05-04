from insteon_mngr.trigger import PLMTrigger
from insteon_mngr.sequences.common import WriteALDBRecord


class WriteALDBRecordModem(WriteALDBRecord):
    def _perform_write(self):
        super()._perform_write()
        if self.in_use is True:
            self.data1 = self._linked_group.device.dev_cat
            self.data2 = self._linked_group.device.sub_cat
            self.data3 = self._linked_group.device.firmware
        msg = self._group.device.create_message('all_link_manage_rec')
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
        trigger = PLMTrigger(plm=self._group.device,
                             attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._save_record()
        trigger.name = self._group.device.dev_addr_str + 'write_aldb'
        trigger.queue()
        self._group.device.queue_device_msg(msg)

    def _ctrl_code(self, search_bytes):
        records = self._group.device.aldb.get_matching_records(search_bytes)
        ctrl_code = 0x20
        if len(records) == 0 and self.controller is True:
            ctrl_code = 0x40
        if len(records) == 0 and self.controller is False:
            ctrl_code = 0x41
        return ctrl_code

    def _compiled_record(self):
        ret = super()._compiled_record()
        del ret['msb']
        del ret['lsb']
        if not self.in_use:
            record = self._group.device.aldb[self.key]
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
        compiled = self._compiled_record()
        aldb_entry = bytearray([
            compiled['link_flags'],
            compiled['group'],
            compiled['dev_addr_hi'],
            compiled['dev_addr_mid'],
            compiled['dev_addr_low'],
            compiled['data_1'],
            compiled['data_2'],
            compiled['data_3']
        ])
        if self.in_use is False:
            aldb_entry = bytearray(8)
        record = self._group.device.aldb[self.key]
        record.edit_record(aldb_entry)
        self.on_success()

    def _write_failure(self):
        self.on_failure()

    def start(self):
        '''Starts the sequence to write the aldb record'''
        if self.linked_group is None and self.in_use:
            print('error no linked_group defined')
        else:
            self._perform_write()
