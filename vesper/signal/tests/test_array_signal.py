import datetime

import numpy as np

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_signal import ArraySignal
from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.sample_array_axis import SampleArrayAxis
from vesper.signal.tests.axis_units import FREQ_UNITS, POWER_UNITS
from vesper.signal.tests.test_signal import SignalTests
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch


class ArraySignalTests(TestCase):


    @staticmethod
    def assert_signal(
            s, name, parent, time_axis, sample_array_axes, amplitude_axis,
            samples):
        
        SignalTests.assert_signal(
            s, name, parent, time_axis, sample_array_axes, amplitude_axis)
        
        assert s.dtype == samples.dtype
        assert np.alltrue(s[:] == samples)

        
    def test_init(self):
        
        start_index = 5
        length = 10
        sample_rate = 2
        spectrum_size = 9
        bin_size = 20
        
        name = 'Signal'
        
        # In practice the parent of a `Signal` will be either a
        # `MultichannelSignal` or `None`. We use a string here for simplicity.
        parent = 'Parent'
        
        reference = Bunch(index=start_index, datetime=datetime.datetime.now())
        time_axis = TimeAxis(
            start_index, length, sample_rate, reference_datetime=reference)
        
        frequency_axis = SampleArrayAxis(
            name='Frequency', units=FREQ_UNITS, length=spectrum_size,
            index_to_value_mapping=LinearMapping(bin_size))
        sample_array_axes = [frequency_axis]
        
        power_axis = AmplitudeAxis(name='Power', units=POWER_UNITS)
        
        samples = np.arange(length * spectrum_size)
        
        args = (name, parent, time_axis, sample_array_axes, power_axis, samples)
        
        s = ArraySignal(*args)
        
        self.assert_signal(s, *args)
