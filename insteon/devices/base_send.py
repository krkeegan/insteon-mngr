'''A send handler provides the device specific functions needed to send messages
to a device.  The declaring code is generic to all devices, but which may
require specific enablement code for a device is linked to from the device
object.  As such, I believe the only code that should need direct access to the
send handler besides the device code, is the device specific function or
rcvd handler code.'''


class BaseSendHandler(object):
    '''Provides a shell of the functions that all send handlers must support'''

    def __init__(self, device):
        '''The base send handler object inherited by all send handlers'''
        self._device = device

    def create_message(self, command_name):
        '''Creates a message object based on the command_name passed'''
        return NotImplemented

    def send_command(self, command_name, state=''):
        '''Creates a message based on the command_name and queues it to be sent
        to the device using the state_machine of state of defined'''
        return NotImplemented
