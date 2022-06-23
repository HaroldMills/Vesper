from vesper.signal.sample_read_delegate import SampleReadDelegate
from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
from vesper.signal.tests.signal_test_case import SignalTestCase
import vesper.signal.tests.utils as utils


class SignalTests(SignalTestCase):


    def test_init(self):
        
        cases = [
            ('A', 0, 0, (), 'int16'),
            ('B', 2, 0, (2,), 'float'),
            ('Bobo', 0, 3, (3, 4), '<i2'),
            ('Bibi', 1, 2, (5, 6, 7), '<i4'),
        ]
        
        frame_rate = 24000
        
        for name, length, channel_count, array_shape, sample_type in cases:
            
            time_axis = TimeAxis(length, frame_rate)
            shape = (channel_count, length) + array_shape
            samples = utils.create_samples(shape, sample_type=sample_type)
            read_delegate = _SampleReadDelegate(samples)
            
            
            # Test initializer with specified name.
            
            s = Signal(
                time_axis, channel_count, array_shape, sample_type,
                read_delegate, name)
            
            self.assert_signal(
                s, name, time_axis, channel_count, array_shape, sample_type,
                samples)
        
        
            # Test initializer with default name.
            
            s = Signal(
                time_axis, channel_count, array_shape, sample_type,
                read_delegate)
            
            self.assert_signal(
                s, 'Signal', time_axis, channel_count, array_shape,
                sample_type, samples)
    
    
class _SampleReadDelegate(SampleReadDelegate):
    
    def __init__(self, samples):
        super().__init__(False)
        self._samples = samples
        
    def read(self, first_slice, second_slice):
        return self._samples[first_slice, second_slice]
