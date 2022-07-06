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
        
        for (name, frame_count, channel_count, sample_array_shape,
                sample_type) in cases:
            
            time_axis = TimeAxis(frame_count, frame_rate)
            shape = (channel_count, frame_count) + sample_array_shape
            samples = utils.create_samples(shape, sample_type=sample_type)
            
            
            # Test initializer with specified name.
            
            s = _TestSignal(
                time_axis, channel_count, sample_array_shape, sample_type,
                samples, name)
            
            self.assert_signal(
                s, name, time_axis, channel_count, sample_array_shape,
                sample_type, samples)
        
        
            # Test initializer with default name.
            
            s = _TestSignal(
                time_axis, channel_count, sample_array_shape, sample_type,
                samples)
            
            self.assert_signal(
                s, 'Signal', time_axis, channel_count, sample_array_shape,
                sample_type, samples)
    
    
class _TestSignal(Signal):
   

    def __init__(
            self, time_axis, channel_count, sample_array_shape, sample_type,
            samples, name=None):

        super().__init__(
            time_axis, channel_count, sample_array_shape, sample_type, name)

        self._samples = samples
        

    def _read(self, frame_slice, channel_slice):
        return self._samples[channel_slice, frame_slice], False
