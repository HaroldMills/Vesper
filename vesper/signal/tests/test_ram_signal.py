import itertools
import numpy as np
import random

from vesper.signal.ram_signal import RamSignal
from vesper.signal.tests.test_signal import SignalTests
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class RamSignalTests(TestCase):


    @staticmethod
    def assert_ram_signal(s, name, samples, frame_rate):
        
        shape = samples.shape
        frame_count = shape[0]
        channel_count = shape[1]
        array_shape = shape[2:]
        
        time_axis = TimeAxis(frame_count, frame_rate)
        
        dtype = samples.dtype
        
        SignalTests.assert_signal(
            s, name, time_axis, channel_count, array_shape, dtype)
        
        for i in range(channel_count):
            
            c = s.channels[i]
            
            SignalTests.assert_channel(
                c, s, str(i), i, time_axis, array_shape, dtype)
            
            utils.assert_arrays_equal(c[:], samples[:, i], strict=True)
        
        
    def test_init(self):
         
        names = ['Bobo', None]
        
        shapes = [
            (0, 0),
            (2, 0),
            (0, 2),
            (1, 2),
            (1, 2, 3),
            (2, 3),
            (2, 3, 4),
            (4, 2, 3, 4)
        ]
         
        frame_rates = [24000, 44100]
         
        dtypes = ['<i2', np.dtype('float')]
         
        cases = itertools.product(names, shapes, frame_rates, dtypes)
         
        for name, shape, frame_rate, dtype in cases:
            
            expected_name = name if name is not None else 'Signal'
            
            samples = utils.create_samples(shape, dtype=dtype)
            channel_first_samples = np.swapaxes(samples, 0, 1)
            
            s = _create_ram_signal(samples, frame_rate, name=name)
            
            self.assert_ram_signal(s, expected_name, samples, frame_rate)
            
            time_axis = TimeAxis(shape[0], frame_rate)
            
            s = _create_ram_signal(
                channel_first_samples, time_axis, samples_channel_first=True,
                name=name)
            
            self.assert_ram_signal(s, expected_name, samples, frame_rate)
            
            
    def test_indexing(self):
        
        frame_count = 5
        channel_count = 2
        sample_array_shape = (2, 3)
        test_count = 1000
        
        # Construct test samples.
        shape = (frame_count, channel_count) + sample_array_shape
        n = np.prod(shape)
        samples = np.arange(n).reshape(shape)
        
        # Construct test signal.
        s = RamSignal(samples, 24000)
        
        # Test frame-first indexing.
        test_indexing(s.as_frames, samples, test_count)
        
        # Test channel-first indexing.
        expected = np.swapaxes(samples, 0, 1)
        test_indexing(s.as_channels, expected, test_count)
        
        # Test channel indexing.
        for i in range(channel_count):
            c = s.channels[i]
            expected = np.swapaxes(samples, 0, 1)[i]
            test_indexing(c, expected, test_count)
            
        
def test_indexing(x, expected, test_count):
    
    shape = expected.shape
    
    for _ in range(test_count):
        
        index_count = random.randrange(len(shape)) + 1
        
        if index_count == 1:
            key = _get_test_index(shape[0])
            
        else:
            key = tuple(_get_test_index(n) for n in shape[:index_count])
            
        # print(key, x[key], expected[key])
        
        utils.assert_arrays_equal(x[key], expected[key], strict=True)
    
    
def _get_test_index(n):
    
    index_type = random.choice(('number', 'range', 'colon'))
    
    if index_type == 'number':
        return random.randrange(n)
    
    elif index_type == 'range':
        start = random.randrange(-n, n)
        stop = random.randrange(-n, n)
        return slice(start, stop)
    
    else:
        return slice(None, None, None)
    
    
def _create_ram_signal(
        samples, frame_rate, samples_channel_first=False, name=None):
    
    kwargs = {}
    
    if samples_channel_first:
        kwargs['samples_channel_first'] = True
        
    if name is not None:
        kwargs['name'] = name
        
    return RamSignal(samples, frame_rate, **kwargs)
