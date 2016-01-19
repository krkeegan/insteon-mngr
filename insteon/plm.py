import serial

from insteon.modem import Modem


class PLM(Modem):

    def __init__(self, core, **kwargs):
        super().__init__(core, self, **kwargs)
        self.set_ack_time(75)
        self.attribute('type', 'plm')
        port = ''
        if 'attributes' in kwargs:
            port = kwargs['attributes']['port']
        elif 'port' in kwargs:
            port = kwargs['port']
        else:
            print('you need to define a port for this plm')
        self.attribute('port', port)
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=19200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0
            )
        except serial.serialutil.SerialException:
            print('unable to connect to port', port)
            self.port_active = False
        self.setup()

    @property
    def port(self):
        return self.attribute('port')

    def _read(self):
        '''Reads bytes from PLM and loads them into a buffer'''
        if self.port_active:
            while self._serial.inWaiting() > 0:
                self._read_buffer.extend(self._serial.read())

    def _write(self, msg):
        self._serial.write(msg)
