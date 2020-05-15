"""Module containing class `Spectrogram`."""


import numpy as np

from vesper.signal.sample_provider import SampleProvider
from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
import vesper.util.time_frequency_analysis_utils as tfa_utils


class Spectrogram(Signal):
    
    
    def __init__(self, waveform, settings, name=None):
        
        if name is None:
            name = 'Spectrogram'
            
        time_axis = _create_time_axis(waveform.time_axis, settings)
        channel_count = len(waveform.channels)
        array_shape = _get_array_shape(settings)
        dtype = 'float64'
        sample_provider = _SampleProvider(waveform, settings, dtype)
        
        super().__init__(
            time_axis, channel_count, array_shape, dtype, sample_provider,
            name)
        
        
def _create_time_axis(waveform_time_axis, settings):
    
    window_size = len(settings.window)
    hop_size = settings.hop_size
    
    length = _get_gram_frame_count(
        waveform_time_axis.length, window_size, hop_size)
    
    frame_rate = waveform_time_axis.frame_rate / hop_size
    
    # The time of a spectrum is the center time of the waveform samples
    # from which it is computed.
    window_center_index = (window_size - 1) / 2
    offset = waveform_time_axis.index_to_time(window_center_index)
    
    return TimeAxis(length, frame_rate, offset)


def _get_gram_frame_count(waveform_frame_count, window_size, hop_size):
    if waveform_frame_count < window_size:
        return 0
    else:
        return 1 + (waveform_frame_count - window_size) // hop_size


def _get_array_shape(settings):
    spectrum_size = settings.dft_size // 2 + 1
    return (spectrum_size,)


class _SampleProvider(SampleProvider):
    
    
    def __init__(self, waveform, settings, dtype):
        self._waveform = waveform
        self._settings = settings
        self._dtype = dtype
        self._array_shape = (self._settings.dft_size // 2 + 1,)
        super().__init__(False)
        
        
    def get_samples(self, channel_key, frame_key):
        
        start_channel, end_channel = _get_bounds(channel_key)
        channel_count = end_channel - start_channel
        
        start_frame, end_frame = _get_bounds(frame_key)
        frame_count = end_frame - start_frame
        
        if channel_count == 0 or frame_count == 0:
            # result will be empty
            
            result = np.array([], dtype=self._dtype)
            
        elif channel_count == 1:
            # result will have one channel
            
            result = self._compute_channel_gram(
                start_channel, start_frame, end_frame)
            
        else:
            # result will have more than one channel
            
            grams = [
                self._compute_channel_gram(i, start_frame, end_frame)
                for i in range(start_channel, end_channel)]
            
            # Stacking separate channel spectrograms into a single,
            # multichannel array doubles the storage we use to compute
            # spectrograms. It would be preferable to allocate a single
            # sample array up front and then compute the channel
            # spectrograms one at a time into that array, obviating the
            # the separate stacking operation. Unfortunately, however,
            # the NumPy FFT function (`numpy.fft.rfft`) that we use to
            # compute the channel spectrograms does not allow
            # specification of the output array.
            result = np.stack(grams)
            
        # Set result shape according to channel and frame keys,
        # eliminating dimensions for which the keys are integers.
        shape = self._get_result_shape(channel_key, frame_key)
        
        return result.reshape(shape)
        
        
    def _compute_channel_gram(self, channel_num, start_frame, end_frame):
        
        s = self._settings
        window_size = len(s.window)
        hop_size = s.hop_size
        
        start = start_frame * hop_size
        
        gram_frame_count = end_frame - start_frame
        waveform_frame_count = _get_waveform_frame_count(
            gram_frame_count, window_size, hop_size)
        end = start + waveform_frame_count
        
        samples = self._waveform.channels[channel_num][start:end]
        
        gram = tfa_utils.compute_spectrogram(
            samples, s.window, hop_size, s.dft_size)
        
        tfa_utils.scale_spectrogram(gram, out=gram)
        
        return gram
        

    def _get_result_shape(self, channel_key, frame_key):
        channel_dim = _get_dim(channel_key)
        frame_dim = _get_dim(frame_key)
        return channel_dim + frame_dim + self._array_shape
    
    
def _get_bounds(key):
    if isinstance(key, int):
        return key, key + 1
    else:
        return key.start, key.stop
    
    
def _get_waveform_frame_count(gram_frame_count, window_size, hop_size):
    if gram_frame_count == 0:
        return 0
    else:
        return window_size + (gram_frame_count - 1) * hop_size
    
    
def _get_dim(key):
    if isinstance(key, int):
        return ()
    else:
        count = key.stop - key.start
        return (count,)
