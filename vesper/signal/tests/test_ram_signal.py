import itertools
import numpy as np

from vesper.signal.ram_signal import RamSignal
from vesper.signal.tests.signal_test_case import SignalTestCase
from vesper.signal.time_axis import TimeAxis
import vesper.signal.tests.utils as utils


class RamSignalTests(SignalTestCase):


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
        
        # We don't test with an int16 sample type since the int16 value
        # range is not large enough to accomodate some test sample values.
        sample_types = ['int32', np.dtype('float')]
        
        cases = itertools.product(names, shapes, frame_rates, sample_types)
        
        for name, shape, frame_rate, sample_type in cases:
        
            expected_name = 'Signal' if name is None else name
            time_axis = TimeAxis(shape[0], frame_rate)
            channel_count = shape[1]
            sample_array_shape = shape[2:]
            samples_f = utils.create_samples(shape, sample_type=sample_type)
            samples_c = np.swapaxes(samples_f, 0, 1)
            
            # Frame rate and frame-first samples.
            s = RamSignal(frame_rate, samples_f, True, name)
            self.assert_signal(
                s, expected_name, time_axis, channel_count, sample_array_shape,
                sample_type, samples_c)
    
            # Time axis and rame-first samples.
            s = RamSignal(time_axis, samples_f, True, name)
            self.assert_signal(
                s, expected_name, time_axis, channel_count, sample_array_shape,
                sample_type, samples_c)
            
            
    def test_init_errors(self):
        
        # sample array with fewer than two dimensions
        self.assert_raises(ValueError, RamSignal, 24000, np.arange(10), False)
        
        # frame count mismatch
        time_axis = TimeAxis(10, 24000)
        samples = np.arange(11).reshape((1, -1))
        self.assert_raises(ValueError, RamSignal, time_axis, samples, False)
