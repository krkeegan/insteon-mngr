from insteon.devices.generic_rcvd import GenericRcvdHandler
from insteon.devices.generic_send import GenericSendHandler
from insteon.devices.generic_functions import GenericFunctions
from insteon.devices.group import (GroupFunctions, GroupSendHandler,
    PLMGroupSendHandler)

def select_device(device=None, dev_cat=0x00, sub_cat=0x00,
                  firmware=0x00, engine_version=0x00):
    # TODO we will have to do something with this eventually
    ret = {}
    ret['functions'] = GenericFunctions(device)
    ret['send_handler'] = GenericSendHandler(device)
    ret['rcvd_handler'] = GenericRcvdHandler(device)
    if engine_version > 0x00:
        pass
    return ret

def select_group(device=None, dev_cat=0x00, sub_cat=0x00,
                  firmware=0x00, engine_version=0x00):
    # TODO we will have to do something with this eventually
    ret = {}
    ret['functions'] = GroupFunctions(device)
    ret['send_handler'] = GroupSendHandler(device)
    if dev_cat == 0x03:
        ret['send_handler'] = PLMGroupSendHandler(device)
    return ret
