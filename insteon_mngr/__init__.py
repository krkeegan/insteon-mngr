'''A Python library for the Insteon Hub or PLM.  Also provides a user interface
for creating Insteon links.'''
import binascii

def BYTE_TO_HEX(data):
    '''Takes a bytearray or a byte and returns a string
    representation of the hex value'''
    return binascii.hexlify(data).decode().upper()

def BYTE_TO_ID(high, mid, low):
    # pylint: disable=E1305
    ret = ('{:02x}'.format(high, 'x').upper() +
           '{:02x}'.format(mid, 'x').upper() +
           '{:02x}'.format(low, 'x').upper())
    return ret

def ID_STR_TO_BYTES(dev_id_str):
    ret = bytearray(3)
    ret[0] = (int(dev_id_str[0:2], 16))
    ret[1] = (int(dev_id_str[2:4], 16))
    ret[2] = (int(dev_id_str[4:6], 16))
    return ret

from insteon_mngr.core import Insteon_Core

__all__ = ['Insteon_Core']
