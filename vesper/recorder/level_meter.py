import math

import numpy as np

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


_DEFAULT_UPDATE_PERIOD = 1      # seconds
_MAX_ABS_SAMPLE = 1


class LevelMeter(Processor):


    type_name = 'Level Meter'


    @staticmethod
    def parse_settings(settings):

        update_period = float(settings.get(
            'update_period', _DEFAULT_UPDATE_PERIOD))
        
        return Bunch(update_period=update_period)
    

    def __init__(self, name, settings, context, input_info):

        super().__init__(name, settings, context, input_info)

        self._update_period = settings.update_period

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate

        self._rms_values = None
        self._peak_values = None


    @property
    def update_period(self):
        return self._update_period
    

    @property
    def rms_values(self):
        return self._rms_values
    

    @property
    def peak_values(self):
        return self._peak_values
    

    def _start(self):

        self._sums = np.zeros(self._channel_count)
        self._peaks = np.zeros(self._channel_count)

        self._block_size = int(round(self._sample_rate * self._update_period))
        self._accumulated_frame_count = 0


    def _process(self, input_item, finished):
        
        samples = input_item.samples
        frame_count = input_item.frame_count
        
        start_index = 0

        while start_index != frame_count:

            remaining = self._block_size - self._accumulated_frame_count
            n = min(frame_count - start_index, remaining)
            
            # Accumulate squared samples.
            s = samples[:, start_index:start_index + n]
            self._sums += np.sum(s * s, axis=1)

            # Update maximum absolute sample values.
            peaks = np.max(np.abs(samples), axis=1)
            self._peaks = np.maximum(self._peaks, peaks)

            self._accumulated_frame_count += n

            if self._accumulated_frame_count == self._block_size:
                # have accumulated an entire block

                rms_values = np.sqrt(self._sums / self._block_size)
                
                self._rms_values = \
                    rms_samples_to_dbfs(rms_values, _MAX_ABS_SAMPLE)
                
                self._peak_values = \
                    samples_to_dbfs(self._peaks, _MAX_ABS_SAMPLE)
                
                self._sums[:] = 0
                self._peaks[:] = 0
                self._accumulated_frame_count = 0

            start_index += n

        if finished:
            self._rms_values = None
            self._peak_values = None


    def get_status_tables(self):

        value_suffix = '' if self._channel_count == 1 else 's'
        rms_values = _format_levels(self.rms_values)
        peak_values = _format_levels(self.peak_values)
        
        rows = (
            (f'Update period', str(self.update_period)),
            (f'Recent RMS Sample Value{value_suffix} (dBFS)', rms_values),
            (f'Recent Peak Sample Value{value_suffix} (dBFS)', peak_values))

        table = StatusTable(self.name, rows)
        
        return [table]


def _format_levels(levels):

    if levels is None:
        return '-'
    
    else:
        levels = [f'{l:.2f}' for l in levels]
        return ', '.join(levels)


# TODO: Move dBFS functions to `signal_utils` package.


_HALF_SQRT_2 = math.sqrt(2) / 2
_MINUS_INFINITY_DB = -1000


def samples_to_dbfs(samples, full_scale_value):
    return _to_db(np.abs(samples) / full_scale_value)


def rms_samples_to_dbfs(samples, full_scale_value):
    return _to_db(samples / (_HALF_SQRT_2 * full_scale_value))


def _to_db(x):
    masked_array = 20 * np.ma.log10(x)
    return masked_array.filled(_MINUS_INFINITY_DB)
