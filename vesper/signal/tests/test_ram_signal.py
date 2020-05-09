import itertools
import numpy as np

from vesper.signal.ram_signal import RamSignal
from vesper.signal.tests.test_signal import SignalTests
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class RamSignalTests(TestCase):


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
        
        # We don't test with an int16 dtype since the int16 value range
        # is not large enough to accomodate some test sample values.
        dtypes = ['int32', np.dtype('float')]
        
        cases = itertools.product(names, shapes, frame_rates, dtypes)
        
        for name, shape, frame_rate, dtype in cases:
        
            expected_name = 'Signal' if name is None else name
            time_axis = TimeAxis(shape[0], frame_rate)
            channel_count = shape[1]
            array_shape = shape[2:]
            samples_f = utils.create_samples(shape, dtype=dtype)
            samples_c = np.swapaxes(samples_f, 0, 1)
            
            # Frame rate and frame-first samples.
            s = RamSignal(frame_rate, samples_f, True, name)
            SignalTests.assert_signal(
                s, expected_name, time_axis, channel_count, array_shape,
                dtype, samples_c)
    
            # Time axis and rame-first samples.
            s = RamSignal(time_axis, samples_f, True, name)
            SignalTests.assert_signal(
                s, expected_name, time_axis, channel_count, array_shape,
                dtype, samples_c)
