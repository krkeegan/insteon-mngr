import xml.etree.ElementTree as ET
import time
import threading
import queue

import requests

from insteon.base_objects import BYTE_TO_HEX
from insteon.plm import Modem


def hub_thread(hub):
    prev_end_pos = -1
    last_bytestring = ''

    while threading.main_thread().is_alive():
        # Read First
        bytestring = ''
        current_end_pos = 0
        start_time = time.time()

        # Get Buffer Contents
        try:
            response = requests.get('http://' + hub.ip + ':' +
                                    hub.tcp_port + '/buffstatus.xml',
                                    auth=requests.auth.HTTPBasicAuth(
                                        hub.user,
                                        hub.password),
                                    timeout=5)
        except requests.exceptions.Timeout:
            # TODO handle multiple timeouts, close connection or something
            print('-----------Timeout Occurred--------')
            time.sleep(.1)
            continue

        root = ET.fromstring(response.text)
        for response in root:
            if response.tag == 'BS':
                bytestring = response.text
                break

        # Place buffer in sequential order
        current_end_pos = int(bytestring[-2:], 16)
        bytestring = bytestring[current_end_pos:-2] + \
            bytestring[:current_end_pos]

        if last_bytestring != '' and prev_end_pos >= 0:
            new_length = current_end_pos - prev_end_pos
            new_length = (200 + new_length) if new_length < 0 else new_length
            verify_bytestring = bytestring[190 - new_length: 200 - new_length]
            if new_length > 0 and last_bytestring == verify_bytestring:
                # print(bytestring[-new_length:])
                hex_string = bytestring[-new_length:]
                hex_data = bytearray.fromhex(hex_string)
                hub._read_queue.put(bytearray(hex_data))

        last_bytestring = bytestring[-10:]
        prev_end_pos = current_end_pos

        # Now write
        if not hub._write_queue.empty():
            command = hub._write_queue.get()
            cmd_str = BYTE_TO_HEX(command)
            url = ('http://' + hub.ip + ':' +
                   hub.tcp_port + '/3?' + cmd_str + '=I=3')
            try:
                response = requests.get(url,
                                        auth=requests.auth.HTTPBasicAuth(
                                            hub.user,
                                            hub.password),
                                        timeout=3
                                        )
            except requests.exceptions.Timeout:
                # TODO what should happen here, assume it wasn't received?
                # but need to take into account that it was
                print('-----------Timeout In Sending--------')
                time.sleep(.1)
                continue
            last_bytestring = '0000000000'
            prev_end_pos = 0

        # Only hammering at hub server three times per second.  Seems to result
        # in the PLM ACK and device message arriving together, but no more than
        # that. Could consider slowing down, but waiting too long could cause
        # the buffer to overflow and would slow down our responses.  Would also
        # need to increase the hub ack_time accordingly too.
        sleep_time = (start_time + .5) - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
        elif sleep_time < -2:
            seconds = str(round(abs(sleep_time), 2))
            print('warning, hub took', seconds, 'to respond')


class Hub(Modem):

    def __init__(self, core, **kwargs):
        super().__init__(core, **kwargs)
        self.set_ack_time(3000)
        self.attribute('type', 'hub')
        self.user = kwargs.get('user')
        self.password = kwargs.get('password')
        self.ip = kwargs.get('ip')
        self.tcp_port = kwargs.get('tcp_port')
        self._read_queue = queue.Queue()
        self._write_queue = queue.Queue()
        threading.Thread(target=hub_thread, args=[self]).start()
        self.setup()

    @property
    def ip(self):
        return self.attribute('ip')

    @ip.setter
    def ip(self, value):
        self.attribute('ip', value)
        return self.attribute('ip')

    @property
    def tcp_port(self):
        return self.attribute('tcp_port')

    @tcp_port.setter
    def tcp_port(self, value):
        self.attribute('tcp_port', value)
        return self.attribute('tcp_port')

    @property
    def user(self):
        return self.attribute('user')

    @user.setter
    def user(self, value):
        self.attribute('user', value)
        return self.attribute('user')

    @property
    def password(self):
        return self.attribute('password')

    @password.setter
    def password(self, value):
        self.attribute('password', value)
        return self.attribute('password')

    def _read(self):
        if not self._read_queue.empty():
            self._read_buffer.extend(self._read_queue.get())

    def _write(self, msg):
        self._write_queue.put(msg)
