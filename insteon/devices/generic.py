from insteon.msg_schema import COMMAND_SCHEMA
from insteon.plm_message import PLM_Message
from insteon.trigger import Trigger


class GenericCommands (object):
    def __init__(self, device):
        self.device = device

    def send_command(self, command_name, state='', dev_bytes={}):
        message = self.create_message(command_name)
        if message is not None:
            message.insert_bytes_into_raw(dev_bytes)
            message.state_machine = state
            self.device.queue_device_msg(message)

    def create_message(self, command_name):
        ret = None
        try:
            cmd_schema = COMMAND_SCHEMA[command_name]
        except Exception as e:
            print('command not found', e)
        else:
            search_list = [
                ['DevCat', self.device.dev_cat],
                ['SubCat', self.device.sub_cat],
                ['Firmware', self.device.firmware]
            ]
            for search_item in search_list:
                cmd_schema = self._recursive_search_cmd(
                    cmd_schema, search_item)
                if not cmd_schema:
                    # TODO figure out some way to allow queuing prior to devcat
                    print(command_name, ' not available for this device')
                    break
            if cmd_schema is not None:
                command = cmd_schema.copy()
                command['name'] = command_name
                ret = PLM_Message(self.device.plm,
                                  device=self,
                                  plm_cmd='insteon_send',
                                  dev_cmd=command)
        return ret

    def _recursive_search_cmd(self, command, search_item):
        unique_cmd = ''
        catch_all_cmd = ''
        for command_item in command:
            if isinstance(command_item[search_item[0]], tuple):
                if search_item[1] in command_item[search_item[0]]:
                    unique_cmd = command_item['value']
            elif command_item[search_item[0]] == 'all':
                catch_all_cmd = command_item['value']
        if unique_cmd != '':
            return unique_cmd
        elif catch_all_cmd != '':
            return catch_all_cmd
        else:
            return None

    def write_aldb_record(self, msb, lsb):
        # TODO This is only the base structure still need to add more basically
        # just deletes things right now
        dev_bytes = {'msb': msb, 'lsb': lsb}
        self.send_command('write_aldb', '', dev_bytes=dev_bytes)

    def add_plm_to_dev_link(self):
        # Put the PLM in Linking Mode
        # queues a message on the PLM
        message = self.device.plm.create_message('all_link_start')
        plm_bytes = {
            'link_code': 0x01,
            'group': 0x00,
        }
        message.insert_bytes_into_raw(plm_bytes)
        message.plm_success_callback = self.add_plm_to_dev_link_step2
        message.msg_failure_callback = self.add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self.device.plm.queue_device_msg(message)

    def add_plm_to_dev_link_step2(self):
        # Put Device in linking mode
        message = self.create_message('enter_link_mode')
        dev_bytes = {
            'cmd_2': 0x00
        }
        message.insert_bytes_into_raw(dev_bytes)
        message.insteon_msg.device_success_callback = (
            self.add_plm_to_dev_link_step3
        )
        message.msg_failure_callback = self.add_plm_to_dev_link_fail
        message.state_machine = 'link plm->device'
        self.device.queue_device_msg(message)

    def add_plm_to_dev_link_step3(self):
        trigger_attributes = {
            'from_addr_hi': self.device.dev_addr_hi,
            'from_addr_mid': self.device.dev_addr_mid,
            'from_addr_low': self.device.dev_addr_low,
            'link_code': 0x01,
            'plm_cmd': 0x53
        }
        trigger = Trigger(trigger_attributes)
        trigger.trigger_function = lambda: self.add_plm_to_dev_link_step4()
        self.device.plm.trigger_mngr.add_trigger(self.device.dev_addr_str + 'add_plm_step_3', trigger)
        print('device in linking mode')

    def add_plm_to_dev_link_step4(self):
        print('plm->device link created')
        self.device.plm.remove_state_machine('link plm->device')
        self.device.remove_state_machine('link plm->device')
        # Next init step
        self._init_step_2()

    def add_plm_to_dev_link_fail(self):
        print('Error, unable to create plm->device link')
        self.device.plm.remove_state_machine('link plm->device')
        self.device.remove_state_machine('link plm->device')


class GenericMessage (object):
    pass
