from insteon.trigger import InsteonTrigger


class BaseSequence(object):
    def __init__(self, device):
        self._device = device
        self._success = None
        self._failure = None

    @property
    def success_callback(self):
        return self._success

    @success_callback.setter
    def success_callback(self, callback):
        self._success = callback

    @property
    def failure_callback(self):
        return self._failure

    @failure_callback.setter
    def failure_callback(self, callback):
        self._failure = callback

    def start(self):
        return NotImplemented

class StatusRequest(BaseSequence):
    '''Used to request the status of a device.  The neither cmd_1 nor cmd_2 of the
    return message can be predicted so we just hope it is the next direct_ack that
    we receive'''
    def start(self):
        trigger_attributes = {
            'msg_type': 'direct_ack',
            'plm_cmd': 0x50,
            'msg_length': 'standard'
        }
        trigger = InsteonTrigger(device=self._device,
                                 attributes=trigger_attributes)
        trigger.trigger_function = lambda: self._process_status_response()
        self._device.plm.trigger_mngr.add_trigger(self._device.dev_addr_str +
                                                  'status_request',
                                                  trigger)
        self._device.send_handler.send_command('light_status_request')

    def _process_status_response(self):
        msg = self._device._rcvd_handler.last_rcvd_msg
        self._device.set_cached_state(msg.get_byte_by_name('cmd_2'))
        aldb_delta = msg.get_byte_by_name('cmd_1')
        if self._device.attribute('aldb_delta') != aldb_delta:
            print('aldb has changed, rescanning')
            self._device.send_handler.query_aldb()
        elif self.success_callback is not None:
            self._success()

class SetALDBDelta(StatusRequest):
    '''Used to get and store the tracking value for the ALDB Delta'''

    def _process_status_response(self):
        msg = self._device._rcvd_handler.last_rcvd_msg
        self._device.set_cached_state(msg.get_byte_by_name('cmd_2'))
        self._device.set_aldb_delta(msg.get_byte_by_name('cmd_1'))
        if self.success_callback is not None:
            self._success()
