"""Module containing class `Spectrogram`."""


import numpy as np

from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
import vesper.util.time_frequency_analysis_utils as tfa_utils


class Spectrogram(Signal):
    
    
    def __init__(self, waveform, settings, name=None):
        
        self._waveform = waveform
        self._settings = settings

        if name is None:
            name = 'Spectrogram'
            
        time_axis = _create_time_axis(waveform.time_axis, settings)
        channel_count = len(waveform.channels)
        item_shape = _get_item_shape(settings)
        dtype = 'float64'
        
        super().__init__(time_axis, channel_count, item_shape, dtype, name)
        
        
    def _read(self, frame_slice, channel_slice):
        
        # TODO: Consider allocating result array up front and then
        # computing spectrogram in modest-sized segments, copying
        # the segments into the result array as you go. This would
        # reduce the amount of storage required for computing large
        # spectrograms (assuming timely garbage collection) by
        # nearly a factor of two.

        # TODO: Also consider computing spectrograms in parallel in
        # multiple processes.

        frame_count = frame_slice.stop - frame_slice.start
        channel_count = channel_slice.stop - channel_slice.start

        if frame_count == 0 or channel_count == 0:
            # result will be empty
            
            result = np.array([], dtype=self._dtype)
            
        elif channel_count == 1:
            # result will have one channel
            
            result = self._compute_channel_gram(
                channel_slice.start, frame_slice.start, frame_slice.stop)
            
        else:
            # result will have more than one channel
            
            grams = [
                self._compute_channel_gram(
                    i, frame_slice.start, frame_slice.stop)
                for i in range(channel_slice.start, channel_slice.stop)]
            
            # Here we require twice the storage of the result.
            # See TODO above about how we might avoid this. 
            result = np.stack(grams)
            
        # Give result correct shape.
        shape = (channel_count, frame_count) + self._item_shape
        result = result.reshape(shape)

        return result, False
        
        
    def _compute_channel_gram(
            self, channel_index, start_frame_index, end_frame_index):
        
        s = self._settings
        window_size = len(s.window)
        hop_size = s.hop_size
        
        start_index = start_frame_index * hop_size
        
        gram_length = end_frame_index - start_frame_index
        waveform_segment_length = _get_waveform_segment_length(
            gram_length, window_size, hop_size)
        end_index = start_index + waveform_segment_length
        
        samples = self._waveform.channels[channel_index][start_index:end_index]
        
        gram = tfa_utils.compute_spectrogram(
            samples, s.window, hop_size, s.dft_size)
        
        tfa_utils.scale_spectrogram(gram, out=gram)
        
        return gram
        
        
def _create_time_axis(waveform_time_axis, settings):
    
    window_size = len(settings.window)
    hop_size = settings.hop_size
    
    length = _get_gram_length(
         waveform_time_axis.length, window_size, hop_size)
    
    frame_rate = waveform_time_axis.frame_rate / hop_size
    
    # The time of a spectrum is the center time of the waveform samples
    # from which it is computed.
    window_center_index = (window_size - 1) / 2
    offset = waveform_time_axis.index_to_time(window_center_index)
    
    return TimeAxis(length, frame_rate, offset)


def _get_waveform_segment_length(gram_length, window_size, hop_size):
    if gram_length == 0:
        return 0
    else:
        return window_size + (gram_length - 1) * hop_size


def _get_gram_length(waveform_length, window_size, hop_size):
    if waveform_length < window_size:
        return 0
    else:
        return 1 + (waveform_length - window_size) // hop_size


def _get_item_shape(settings):
    spectrum_size = settings.dft_size // 2 + 1
    return (spectrum_size,)
