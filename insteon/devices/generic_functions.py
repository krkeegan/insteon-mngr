class GenericFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_controller_data1(self, responder):
        return 0x03

    def get_controller_data2(self, responder):
        return 0x00

    def get_features(self):
        '''Returns the intrinsic parameters of a device, these are not user
        editable so are not saved in the config.json file'''
        ret = {}
        return ret
