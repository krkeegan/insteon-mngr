import json
import time
import atexit
import signal
import sys

from .plm import PLM
from .hub import Hub



class Insteon_Core(object):
    '''Provides global management functions'''

    def __init__(self):
        self._modems = []
        self._last_saved_time = 0
        self._load_state()
        # Be sure to save before exiting
        atexit.register(self._save_state, True)

    def loop_once(self):
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
        # TODO need to handle checking for existing hub and return it
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
