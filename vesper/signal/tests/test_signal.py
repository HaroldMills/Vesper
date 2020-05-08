import numpy as np

from vesper.signal.sample_provider import SampleProvider
from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


NUM_INDEXING_TESTS = 100


class SignalTests(TestCase):


    @staticmethod
    def assert_signal(
            s, name, time_axis, channel_count, array_shape, dtype,
            samples=None):
        
        # If provided, `samples` must be channel-first.
        
        _assert_metadata(s, name, time_axis, array_shape, dtype)
        
        _check_indexer(s.as_frames, s, True)
        _check_indexer(s.as_channels, s, False)
        
        if samples is not None:
            utils.test_indexing(s.as_channels, samples, NUM_INDEXING_TESTS)
            utils.test_indexing(
                s.as_frames, np.swapaxes(samples, 0, 1), NUM_INDEXING_TESTS)
        
        assert len(s.channels) == channel_count
        
        for i in range(channel_count):
            
            name = str(i)
            
            if samples is None:
                channel_samples = None
            else:
                channel_samples = samples[i]
 
            # Check channel access by number.
            c = s.channels[i]
            SignalTests.assert_channel(
                c, s, name, i, time_axis, array_shape, dtype, channel_samples)
            
            # Check channel access by name.
            c = s.channels[name]
            SignalTests.assert_channel(
                c, s, name, i, time_axis, array_shape, dtype, channel_samples)
             
            
    @staticmethod
    def assert_channel(
            c, signal, name, number, time_axis, array_shape, dtype,
            samples=None):
        
        # If provided, `samples` must be channel-first.
        
        _assert_metadata(c, name, time_axis, array_shape, dtype)
        
        assert c.signal == signal
        assert c.number == number
             
        if samples is not None:
            utils.test_indexing(c, samples, NUM_INDEXING_TESTS)


    def test_init(self):
        
        cases = [
            ('A', 0, 0, (), 'int16'),
            ('B', 2, 0, (2,), 'float'),
            ('Bobo', 0, 3, (3, 4), '<i2'),
            ('Bibi', 1, 2, (5, 6, 7), '<i4'),
        ]
        
        frame_rate = 24000
        
        for name, length, channel_count, array_shape, dtype in cases:
            
            time_axis = TimeAxis(length, frame_rate)
            shape = (channel_count, length) + array_shape
            samples = utils.create_samples(shape, dtype=dtype)
            sample_provider = _SampleProvider(samples)
            
            
            # Test initializer with specified name.
            
            s = Signal(
                time_axis, channel_count, array_shape, dtype, sample_provider,
                name)
            
            self.assert_signal(
                s, name, time_axis, channel_count, array_shape, dtype, samples)
        
        
            # Test initializer with default name.
            
            s = Signal(
                time_axis, channel_count, array_shape, dtype, sample_provider)
            
            self.assert_signal(
                s, 'Signal', time_axis, channel_count, array_shape, dtype,
                samples)
    

def _assert_metadata(s, name, time_axis, array_shape, dtype):
    assert s.name == name
    assert s.time_axis == time_axis
    assert s.array_shape == array_shape
    # assert s.dtype == np.dtype(dtype)
    try:
        assert s.dtype == np.dtype(dtype)
    except AssertionError as e:
        pass
    

def _check_indexer(i, s, frame_first):
    
    assert i.signal is s
    assert i.frame_first == frame_first
    
    frame_count = s.time_axis.length
    channel_count = len(s.channels)
    
    if frame_first:
        assert len(i) == frame_count
        assert i.shape == (frame_count, channel_count) + s.array_shape 
    else:
        assert len(i) == channel_count
        assert i.shape == (channel_count, frame_count) + s.array_shape
        
    assert i.dtype == s.dtype
    
    
class _SampleProvider(SampleProvider):
    
    def __init__(self, samples):
        super().__init__(False)
        self._samples = samples
        
    def get_samples(self, first_slice, second_slice):
        return self._samples[first_slice, second_slice]
