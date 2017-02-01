class GroupSendHandler(object):
    '''Provides the basic command handling for group object.  Devices, whose
    group has distinct commands and needs should create their own send handler
    class that inherits and overrides the necessary elements'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device


class GroupFunctions(object):
    def __init__(self, device):
        self._device = device


class PLMGroupSendHandler(object):
    '''Provides the basic command handling for plm group object.'''
    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device
