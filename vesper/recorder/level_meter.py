import logging
import math

import numpy as np

from vesper.recorder.processor import Processor
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_UPDATE_PERIOD = 1      # seconds

_SAMPLE_SIZE = 16
_SAMPLE_DTYPE = '<i2'


class LevelMeter(Processor):


    type_name = 'Level Meter'


    @staticmethod
    def parse_settings(settings):

        update_period = float(settings.get(
            'update_period', _DEFAULT_UPDATE_PERIOD))
        
        return Bunch(update_period=update_period)
    

    def __init__(self, name, settings, input_info):

        super().__init__(name, settings, input_info)

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

        # _logger.info(f'_LevelMeter.recording_starting: {time}')

        self._sums = np.zeros(self._channel_count)
        self._peaks = np.zeros(self._channel_count)

        self._block_size = int(round(self._sample_rate * self._update_period))
        self._accumulated_frame_count = 0

        self._full_scale_value = 2 ** (_SAMPLE_SIZE - 1)


    def _process(self, input_item):
        
        # Get NumPy sample array.
        samples = np.frombuffer(input_item.samples, dtype=_SAMPLE_DTYPE)
        
        # Make sample array 2D. Compute frame count from sample array
        # length rather than using `input_item.frame_count`, since the latter
        # may be less than the sample array capacity.
        frame_count = len(samples) // self._channel_count
        samples = samples.reshape((frame_count, self._channel_count))

        # _logger.info(f'LevelMeter._process: {frame_count}')
      
        # Make sample array `float64` to avoid arithmetic overflow in
        # subsequent processing.
        samples = samples.astype(np.float64)

        start_index = 0
        frame_count = input_item.frame_count

        while start_index != frame_count:

            remaining = self._block_size - self._accumulated_frame_count
            n = min(frame_count - start_index, remaining)
            
            # Accumulate squared samples.
            s = samples[start_index:start_index + n]
            self._sums += np.sum(s * s, axis=0)

            # Update maximum absolute sample values.
            peaks = np.max(np.abs(samples), axis=0)
            self._peaks = np.maximum(self._peaks, peaks)

            self._accumulated_frame_count += n

            if self._accumulated_frame_count == self._block_size:
                # have accumulated an entire block

                rms_values = np.sqrt(self._sums / self._block_size)
                
                self._rms_values = rms_samples_to_dbfs(
                    rms_values, self._full_scale_value)
                
                self._peak_values = samples_to_dbfs(
                    self._peaks, self._full_scale_value)
                
                # _logger.info(
                #     f'_LevelMeter: RMS {self._rms_values} '
                #     f'peak {self._peak_values}')
                
                self._sums = np.zeros(self._channel_count)
                self._peaks = np.zeros(self._channel_count)
                self._accumulated_frame_count = 0

            start_index += n


    def _stop(self):
    #    _logger.info(f'_LevelMeter.recording_stopped: {time}')
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

        table = Bunch(title=self.name, rows=rows)
        
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
