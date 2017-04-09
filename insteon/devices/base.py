'''Provides the shell for what a device specific file should provide'''


class Base(object):
    '''The base object for all device specific files'''

    def __init__(self, device):
        # Be careful storing any attributes, this object may be dropped
        # and replaced with a new object in a different class at runtime
        # if the dev_cat changes
        self._device = device

    def create_message(self, command_name):
        '''Creates a message based on the command name provided and returns
        the message'''
        return NotImplemented

    def send_command(self, command_name, state=''):
        '''Creates and sends a message base don the command name, sets the state
        machine to the value passed in state if set'''
        return NotImplemented
