import json
import time
import atexit
import threading

from insteon.plm import PLM
from insteon.hub import Hub
from insteon.config_server import start, stop


class Insteon_Core(object):
    '''Provides global management functions'''

    def __init__(self):
        self._modems = []
        self._last_saved_time = 0
        self._load_state()
        threading.Thread(target=self._core_loop).start()
        # Be sure to save before exiting
        atexit.register(self._save_state, True)

        # Load device data
        with open('insteon/data/device_categories.json', 'r') as myfile:
            json_cats = myfile.read()
        self.device_categories = json.loads(json_cats)

        with open('insteon/data/device_models.json', 'r') as myfile:
            json_models = myfile.read()
        self.device_models = json.loads(json_models)

    def _core_loop(self):
        server = start(self)
        while threading.main_thread().is_alive():
            self._loop_once()
        stop(server)

    def _loop_once(self):
        '''Perform one loop of processing the data waiting to be
        handled by the Insteon Core'''
        for modem in self._modems:
            modem.process_input()
            modem.process_unacked_msg()
            modem.process_queue()
        self._save_state()

    def add_hub(self, **kwargs):
        '''Inform the core of a hub that should be monitored as part
        of the core process'''
        ret = None
        for modem in self._modems:
            if (modem.type == 'hub' and
                    modem.ip == kwargs['ip'] and
                    modem.tcp_port == kwargs['tcp_port']):
                ret = modem
                break
        if ret is None:
            ret = Hub(self, **kwargs)
            if ret is not None:
                self._modems.append(ret)
        return ret

    def add_plm(self, **kwargs):
        '''Inform the core of a plm that should be monitored as part
        of the core process'''
        device_id = ''
        ret = None
        # TODO the check for an existing PLM is a bit clunky, need to check /
        # ID as well (if we moved the PLM to a diff port)
        if 'device_id' in kwargs:
            device_id = kwargs['device_id']
        if 'attributes' in kwargs:
            attributes = kwargs['attributes']
            ret = PLM(self, device_id=device_id, attributes=attributes)
        elif 'port' in kwargs:
            port = kwargs['port']
            for modem in self._modems:
                if modem.attribute('port') == port:
                    ret = modem
            if ret is None:
                ret = PLM(self, device_id=device_id, port=port)
        else:
            print('you need to define a port for this plm')
        if ret is not None:
            self._modems.append(ret)
        return ret

    def get_modem_by_id(self, id):
        ret = None
        for modem in self._modems:
            if modem.dev_addr_str == id:
                ret = modem
        return ret

    def get_all_modems(self):
        ret = []
        for plm in self._modems:
            ret.append(plm)
        return ret

    def _save_state(self, is_exit=False):
        # Saves the config of the entire core to a file
        if self._last_saved_time < time.time() - 60 or is_exit:
            # Save once a minute, on on exit
            out_data = {'Modems': {}}
            for modem in self._modems:
                modem_point = {}
                modem_point = modem._attributes.copy()
                modem_point['ALDB'] = modem._aldb.get_all_records_str()
                modem_point['Devices'] = {}
                out_data['Modems'][modem.dev_addr_str] = modem_point
                for address, device in modem._devices.items():
                    dev_point = device._attributes.copy()
                    dev_point['ALDB'] = device._aldb.get_all_records_str()
                    modem_point['Devices'][address] = dev_point
            try:
                json_string = json.dumps(out_data,
                                         sort_keys=True,
                                         indent=4,
                                         ensure_ascii=False)
            except Exception:
                print ('error writing config to file')
            else:
                outfile = open('config.json', 'w')
                outfile.write(json_string)
                outfile.close()
            self._saved_state = out_data
            self._last_saved_time = time.time()

    def _load_state(self):
        try:
            with open('config.json', 'r') as infile:
                read_data = infile.read()
            read_data = json.loads(read_data)
        except FileNotFoundError:
            read_data = {}
        except ValueError:
            read_data = {}
            print('unable to read config file, skipping')
        if 'Modems' in read_data:
            for modem_id, modem_data in read_data['Modems'].items():
                if modem_data['type'] == 'plm':
                    self.add_plm(attributes=modem_data, device_id=modem_id)
                elif modem_data['type'] == 'hub':
                    self.add_hub(attributes=modem_data, device_id=modem_id)

    def get_device_category(self, cat):
        """Return the device category and name given the category id"""
        cat = '{:02x}'.format(cat, 'x').upper()
        if cat in self.device_categories:
            return self.device_categories[cat]
        else:
            return False


    def get_device_model(self, cat, sub_cat, key=''):
        """Return the model name given cat/subcat or product key"""
        cat = '{:02x}'.format(cat, 'x').upper()
        sub_cat = '{:02x}'.format(sub_cat, 'x').upper()
        if cat + ':' + sub_cat in self.device_models:
            return self.device_models[cat + ':' + sub_cat]
        else:
            for i_key, i_val in self.device_models.items():
                if 'key' in i_val:
                    if i_val['key'] == key:
                        return i_val
            return False

###################################################################
#
# User Accessible functions
#
###################################################################

    def get_linked_devices(self):
        linked_devices = {}
        for modem in self.get_all_modems():
            for device in modem.get_all_devices():
                '''Returns a dictionary of all devices linked to the modem'''
                dev_cat_record = self.get_device_category(device.dev_cat)
                if dev_cat_record and 'name' in dev_cat_record:
                    dev_cat_name = dev_cat_record['name']
                    dev_cat_type = dev_cat_record['type']
                else:
                    dev_cat_name = 'unknown'
                    dev_cat_type = 'unknown'

                linked_dev_model = self.get_device_model(device.dev_cat, device.sub_cat)
                if 'name' in linked_dev_model:
                    dev_model_name = linked_dev_model['name']
                else:
                    dev_model_name = 'unknown'

                if 'sku' in linked_dev_model:
                    dev_sku = linked_dev_model['sku']
                else:
                    dev_sku = 'unknown'

                linked_devices[device.dev_addr_str] = {
                    'cat_name': dev_cat_name,
                    'cat_type': dev_cat_type,
                    'model_name' : dev_model_name,
                    'cat': device.dev_cat,
                    'sub_cat': device.sub_cat,
                    'sku': dev_sku,
                    'group': []
                }

        return linked_devices
