'''Contains the _ALDBSequence class.'''

from insteon_mngr.sequences.common import (BaseSequence, SetALDBDelta,
    StatusRequest)
from insteon_mngr.sequences.i1_device import WriteALDBRecordi1, _WriteMSBi1

class _ALDBSequence(BaseSequence):
    '''This is a specialized sequence that queues and manages all aldb sequences
    for a device.  Only one of these sequences should exist for each device
    which is automatically created and stored in the device aldb object. You
    should not need to ever interact directly with this class.'''
    def __init__(self, device=None):
        super().__init__()
        self._device = device
        self._queue = []
        self._running = False
        self._failure = False
        self._msb = 0x00

    def add_sequence(self, sequence):
        '''Appends an aldb link sequnce onto the queue'''
        self._queue.append(sequence)
        self.start()

    def start(self):
        '''Starts the queue sequence if it is not already running'''
        if self._running is False:
            self._startup()

    def _msb_set(self, msb):
        self._msb = msb
        self._step_complete()

    def _step_complete(self):
        if len(self._queue) == 0:
            self._finish()
        else:
            next_seq = self._queue[0]
            if (isinstance(next_seq, WriteALDBRecordi1) and
                    next_seq.msb != self._msb):
                next_msb = next_seq.msb
                sequence = _WriteMSBi1(device=self._device)
                sequence.msb = next_msb
                sequence.add_success_callback(lambda: self._msb_set(next_msb))
            else:
                sequence = self._queue.pop(0)
                sequence.add_success_callback(self._step_complete)
            sequence.add_failure_callback(self._step_failure)
            sequence.aldb_start()

    def _step_failure(self):
        for sequence in self._queue:
            sequence._on_failure()
        self._failure = True
        self._finished()

    def _startup(self):
        self._running = True
        status_sequence = StatusRequest(group=self._device.base_group)
        status_sequence.add_success_callback(self._step_complete)
        status_sequence.add_failure_callback(self._step_failure)
        status_sequence.start()

    def _finish(self):
        sequence = SetALDBDelta(group=self._device.base_group)
        sequence.add_success_callback(self._finished)
        sequence.add_failure_callback(self._step_failure)
        sequence.start()

    def _finished(self):
        self._running = False
        if self._failure:
            self._on_failure()
        else:
            self._on_success()
