from insteon_mngr.sequences.common import BaseSequence

class DeleteLinkPair(BaseSequence):
    '''Deletes the link pair from the devices'''
    def __init__(self):
        super().__init__()
        self._controller_device = None
        self._responder_device = None
        self._controller_key = None
        self._responder_key = None

    def set_controller_device_with_key(self, device, key):
        self._controller_device = device
        self._controller_key = key

    def set_responder_device_with_key(self, device, key):
        self._responder_device = device
        self._responder_key = key

    def start(self):
        '''Deletes the link pair from the devices'''
        controller_sequence = self._get_link_sequence(self._controller_device,
                                                      self._controller_key)
        responder_sequence = self._get_link_sequence(self._responder_device,
                                                     self._responder_key)
        if responder_sequence is not None and controller_sequence is not None:
            responder_sequence.add_success_callback(lambda: self._on_success())
            controller_sequence.add_success_callback(lambda: responder_sequence.start())
            controller_sequence.start()
        elif responder_sequence is not None:
            responder_sequence.add_success_callback(lambda: self._on_success())
            responder_sequence.start()
        elif controller_sequence is not None:
            controller_sequence.add_success_callback(lambda: self._on_success())
            controller_sequence.start()

    def _get_link_sequence(self, device, key):
        ret = None
        if device is not None and key is not None:
            ret = device.send_handler.delete_record(key=key)
        return ret
