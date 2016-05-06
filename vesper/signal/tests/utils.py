import datetime

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_axis import ArrayAxis
from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.tests.axis_units import FREQ_UNITS, POWER_UNITS
from vesper.signal.time_axis import TimeAxis
from vesper.util.bunch import Bunch


def create_test_spectrogram_axes(
        start_index, length, sample_rate, spectrum_size, bin_size):
    
    reference = Bunch(index=start_index, datetime=datetime.datetime.now())
    time_axis = TimeAxis(
        start_index, length, sample_rate, reference_datetime=reference)
    
    frequency_axis = ArrayAxis(
        name='Frequency', units=FREQ_UNITS, length=spectrum_size,
        index_to_value_mapping=LinearMapping(bin_size))
    array_axes = [frequency_axis]
    
    power_axis = AmplitudeAxis(name='Power', units=POWER_UNITS)
    
    return (time_axis, array_axes, power_axis)
