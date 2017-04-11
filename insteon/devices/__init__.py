from insteon.devices.base_send import BaseSendHandler
from insteon.devices.generic_rcvd import GenericRcvdHandler
from insteon.devices.generic_send import GenericSendHandler
from insteon.devices.generic_functions import GenericFunctions
from insteon.devices.group import (GroupFunctions, GroupSendHandler,
    PLMGroupSendHandler, PLMGroupFunctions)
from insteon.devices.dimmer import DimmerSendHandler, DimmerGroupFunctions
from insteon.devices.modem_send import ModemSendHandler


def select_classes(dev_cat=0x00, sub_cat=0x00,
                   firmware=0x00):
    # TODO this can't eb working right for groups, all groupd would be the same
    ret = {
        'device': {},
        'group': {}
    }
    ret['device']['functions'] = GenericFunctions
    ret['device']['send_handler'] = GenericSendHandler
    ret['device']['rcvd_handler'] = GenericRcvdHandler
    ret['group']['functions'] = GroupFunctions
    ret['group']['send_handler'] = GroupSendHandler
    if dev_cat == 0x01:
        ret['device']['send_handler'] = DimmerSendHandler
        ret['group']['functions'] = DimmerGroupFunctions
    elif dev_cat == 0x03:
        ret['device']['functions'] = None
        ret['device']['send_handler'] = None
        ret['device']['rcvd_handler'] = None
        ret['group']['send_handler'] = PLMGroupSendHandler
        ret['group']['functions'] = PLMGroupFunctions
    return ret
