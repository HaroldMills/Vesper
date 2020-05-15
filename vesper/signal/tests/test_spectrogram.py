import numpy as np

from vesper.signal.ram_signal import RamSignal
from vesper.signal.spectrogram import Spectrogram
from vesper.signal.tests.test_signal import SignalTests
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
import vesper.util.time_frequency_analysis_utils as tfa_utils


class SpectrogramTests(TestCase):


    def test_init(self):
        
        channel_count = 2
        waveform_frame_count = 32
        waveform_frame_rate = 16000
        window_size = 16
        hop_size = 8
        dft_size = 16
        
        samples = _get_waveform_samples(
            channel_count, waveform_frame_count, window_size)
        waveform = RamSignal(waveform_frame_rate, samples, False)
        
        window = np.ones(window_size)
        settings = Bunch(window=window, hop_size=hop_size, dft_size=dft_size)        
        gram = Spectrogram(waveform, settings)
        
        gram_frame_count = 1 + (waveform_frame_count - window_size) // hop_size
        gram_frame_rate = waveform_frame_rate / hop_size
        offset = (window_size - 1) / 2 / waveform_frame_rate
        time_axis = TimeAxis(gram_frame_count, gram_frame_rate, offset)
        
        array_shape = ((dft_size // 2) + 1,)
        
        samples = _get_gram_samples(waveform, window, hop_size, dft_size)
        
        SignalTests.assert_signal(
            gram, 'Spectrogram', time_axis, channel_count, array_shape,
            'float64', samples)
        
        # _show_samples(gram)


def _get_waveform_samples(channel_count, frame_count, window_size):
    
    channel_samples = [
        _get_waveform_channel_samples(i, frame_count, window_size)
        for i in range(channel_count)]
    
    return np.stack(channel_samples)
    
    
def _get_waveform_channel_samples(channel_num, frame_count, window_size):
    phase_factor = 2 * np.pi / window_size
    return np.cos(channel_num * np.arange(frame_count) * phase_factor)


def _get_gram_samples(waveform, window, hop_size, dft_size):
    
    channels = waveform.channels
    
    channel_samples = [
        _get_gram_channel_samples(channels[i][:], window, hop_size, dft_size)
        for i in range(len(channels))]
    
    return np.stack(channel_samples)


def _get_gram_channel_samples(waveform_samples, window, hop_size, dft_size):
    
    gram = tfa_utils.compute_spectrogram(
        waveform_samples, window, hop_size, dft_size)
    
    tfa_utils.scale_spectrogram(gram, out=gram)
    
    return gram
    
    
def _show_samples(gram):
    print(gram.as_channels[:])
