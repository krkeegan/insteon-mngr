import json
import time
import atexit
import threading
import random
import os
import pkg_resources

from insteon_mngr.plm import PLM
from insteon_mngr.hub import Hub
from insteon_mngr.config_server import start, stop


class Insteon_Core(object):
    '''Provides global management functions'''

    def __init__(self, config_path=None):
        if config_path is None:
            os.makedirs(os.path.join(os.path.expanduser("~"),'.insteon_mngr'),
                        exist_ok=True)
            self._config_path = os.path.join(os.path.expanduser("~"),
                                             '.insteon_mngr',
                                             'config.json')
        else:
            self._config_path = os.path.join(config_path, 'config.json')
        self._modems = []
        self._last_saved_time = 0
        self._load_state()
        threading.Thread(target=self._core_loop).start()
        # Be sure to save before exiting
        atexit.register(self._save_state, True)

        # Load device data
        json_cats = pkg_resources.resource_string(__name__, "/data/device_categories.json")
        self.device_categories = json.loads(json_cats.decode())

        json_models = pkg_resources.resource_string(__name__, "/data/device_models.json")
        self.device_models = json.loads(json_models.decode())

    def _get_all_user_links(self):
        ret = {}
        for modem in self.get_all_modems():
            ret.update(modem.get_all_user_links())
            for device in modem.get_all_devices():
                ret.update(device.get_all_user_links())
        return ret

    def get_new_user_link_unique_id(self):
        '''Returns an integer between 100,000 and 999,999 that is not used by
        an existing user_link as a uid'''
        rand = random.randint(100000,999999)
        all_links = self._get_all_user_links()
        while rand in all_links:
            rand = random.randint(100000,999999)
        return rand

    def get_user_links_for_this_controller(self, controller_group):
        all_links = self._get_all_user_links()
        ret = {}
        for uid, link in all_links.items():
            if controller_group == link.controller_group:
                ret[uid] = link
        return ret

    def get_user_links_for_this_controller_device(self, controller_device):
        all_links = self._get_all_user_links()
        ret = {}
        for uid, link in all_links.items():
            if controller_device == link.controller_device:
                ret[uid] = link
        return ret

    def find_user_link(self, search_uid):
        ret = None
        all_links = self._get_all_user_links()
        for link_uid in all_links:
            if search_uid == link_uid:
                ret = all_links[link_uid]
        return ret

    def get_matching_aldb_records(self, attributes):
        ret = []
        for modem in self.get_all_modems():
            ret.extend(modem.aldb.get_matching_records(attributes))
            for device in modem.get_all_devices():
                ret.extend(device.aldb.get_matching_records(attributes))
        return ret

    def _core_loop(self):
        server = start(self)
        while threading.main_thread().is_alive():
            self._loop_once()
            time.sleep(.05)
        stop(server)

    def _loop_once(self):
        '''Perform one loop of processing the data waiting to be
        handled by the Insteon Core'''
        for modem in self._modems:
            modem.process_input()
            modem.process_unacked_msg()
            modem.process_queue()
        self._save_state()

    def _save_device(self, device):
        ret = device._attributes.copy()
        ret['aldb'] = device.aldb.get_all_records_str()
        ret['groups'] = device.save_groups()
        ret['user_links'] = device.save_user_links()
        return ret

    def _save_state(self, is_exit=False):
        # Saves the config of the entire core to a file
        if self._last_saved_time < time.time() - 60 or is_exit:
            # Save once a minute, on on exit
            out_data = {'modems': {}}
            for modem in self._modems:
                out_data['modems'][modem.dev_addr_str] = self._save_device(modem)
                out_data['modems'][modem.dev_addr_str]['devices'] = {}
                for address, device in modem._devices.items():
                    out_data['modems'][modem.dev_addr_str]['devices'][address] = \
                        self._save_device(device)
            try:
                json_string = json.dumps(out_data,
                                         sort_keys=True,
                                         indent=4,
                                         ensure_ascii=False)
            except Exception:
                print('error writing config to file')
            else:
                outfile = open(self._config_path, 'w')
                outfile.write(json_string)
                outfile.close()
            self._saved_state = out_data
            self._last_saved_time = time.time()

    def _load_state(self):
        try:
            with open(self._config_path, 'r') as infile:
                read_data = infile.read()
            read_data = json.loads(read_data)
        except FileNotFoundError:
            read_data = {}
        except ValueError:
            read_data = {}
            print('unable to read config file, skipping')
        if 'modems' in read_data:
            for modem_id, modem_data in read_data['modems'].items():
                if modem_data['type'] == 'plm':
                    self.add_plm(attributes=modem_data, device_id=modem_id)
                elif modem_data['type'] == 'hub':
                    self.add_hub(attributes=modem_data, device_id=modem_id)

    # TODO not sure these should be methods, perhaps better as functions

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
            for i_val in self.device_models.values():
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
        '''Returns a dictionary of all devices defined in the core.'''
        linked_devices = {}
        for modem in self.get_all_modems():
            for device in modem.get_all_devices():
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

    def add_hub(self, **kwargs):
        '''Inform the core of a hub that should be monitored as part
        of the core process'''
        ret = None
        for modem in self._modems:
            if (modem.type == 'hub' and
                    modem.ip == kwargs['ip'] and
                    modem.port == kwargs['port']):
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

    def get_device_by_addr(self, addr):
        ret = None
        for modem in self._modems:
            if addr.lower() == modem.dev_addr_str.lower():
                ret = modem
            else:
                ret = modem.get_device_by_addr(addr)
                if ret is not None:
                    break
        if ret is None:
            #print('error, unknown device address=', addr)
            pass
        return ret

    def get_all_modems(self):
        ret = []
        for plm in self._modems:
            ret.append(plm)
        return ret
