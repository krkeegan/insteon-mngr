from insteon.sequences import WriteALDBRecordi2, WriteALDBRecordi1


class GenericFunctions(object):
    def __init__(self, device):
        self._device = device

    def get_responder_data3(self):
        ret = self._device.group
        if ret == 0x01:
            ret = 0x00
        return ret

    def create_responder_link(self, linked_device, is_on=True):
        if self._device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self._device)
        else:
            link_sequence = WriteALDBRecordi1(self._device)
        link_sequence.controller = False
        link_sequence.linked_device = linked_device
        on_level = 0x00
        if is_on:
            on_level = 0xFF
        link_sequence.data1 = on_level
        link_sequence.data2 = 0x00
        link_sequence.start()

    def create_controller_link(self, linked_device):
        if self._device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self._device)
        else:
            link_sequence = WriteALDBRecordi1(self._device)
        link_sequence.controller = True
        link_sequence.linked_device = linked_device
        link_sequence.data1 = 0x03
        link_sequence.data2 = 0x00
        link_sequence.start()

    def delete_record(self, address=bytearray(2)):
        if self._device.engine_version > 0x00:
            link_sequence = WriteALDBRecordi2(self._device)
        link_sequence.address = address
        link_sequence.in_use = False
        link_sequence.start()
