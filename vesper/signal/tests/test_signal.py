from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
from vesper.signal.tests.signal_test_case import SignalTestCase
import vesper.signal.tests.utils as utils


class SignalTests(SignalTestCase):


    def test_init(self):
        
        # Be careful about numbers of channels and dtypes in the test
        # cases. In particular, don't use more than two channels for
        # 16-bit integer dtypes, or `utils.create_samples` will return
        # 32-bit integer samples because of some sort of NumPy type
        # promotion that happens to accommodate sample values that are
        # too large for 16 bits.
        cases = [
            ('A', 0, 0, (), 'int16'),
            ('B', 2, 0, (2,), 'float'),
            ('Bobo', 0, 2, (3, 4), '<i4'),
            ('Bibi', 1, 3, (5, 6, 7), '<i4'),
        ]
        
        frame_rate = 24000
        
        for name, frame_count, channel_count, sample_array_shape, dtype in \
                cases:
            
            time_axis = TimeAxis(frame_count, frame_rate)
            shape = (channel_count, frame_count) + sample_array_shape
            samples = utils.create_samples(shape, dtype=dtype)
            
            
            # Test initializer with specified name.
            
            s = _TestSignal(
                time_axis, channel_count, sample_array_shape, dtype, samples,
                name)
            
            self.assert_signal(
                s, name, time_axis, channel_count, sample_array_shape, dtype,
                samples)
        
        
            # Test initializer with default name.
            
            s = _TestSignal(
                time_axis, channel_count, sample_array_shape, dtype, samples)
            
            self.assert_signal(
                s, 'Signal', time_axis, channel_count, sample_array_shape,
                dtype, samples)
    
    
class _TestSignal(Signal):
   

    def __init__(
            self, time_axis, channel_count, sample_array_shape, dtype,
            samples, name=None):

        super().__init__(
            time_axis, channel_count, sample_array_shape, dtype, name)

        self._samples = samples
        

    def _read(self, frame_slice, channel_slice):
        return self._samples[channel_slice, frame_slice], False
