"""Utility functions and constants for signal class unit tests."""


from numbers import Number
import datetime

import numpy as np

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_axis import ArrayAxis
from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.time_axis import TimeAxis
from vesper.util.bunch import Bunch


DEFAULT_UNITS = Bunch(plural=None, singular=None, abbreviation=None)
TIME_UNITS = Bunch(plural='seconds', singular='second', abbreviation='S')
FREQ_UNITS = Bunch(plural='hertz', singular='hertz', abbreviation='Hz')
POWER_UNITS = Bunch(plural='decibels', singular='decibel', abbreviation='dB')


def test_init(args, defaults, cls, check):
    
    for i in range(len(args)):
        some_args = args[:i]
        a = cls(*some_args)
        expected = args[:i] + defaults[i:]
        check(a, *expected)


def test_eq(cls, args, changes):
    
    a = cls(*args)
    
    b = cls(*args)
    assert a == b
    
    for i in range(len(changes)):
        changed_args = args[:i] + (changes[i],) + args[i + 1:]
        b = cls(*changed_args)
        assert a != b


def test_mapping(a, forward_name, inverse_name, cases):
     
    for x, y in cases:
         
        method = getattr(a, forward_name)
        result = method(x)
        assert_numbers_or_arrays_equal(result, y)
          
        method = getattr(a, inverse_name)
        result = method(y)
        assert_numbers_or_arrays_equal(result, x)
         
         
def assert_numbers_or_arrays_equal(x, y):
    if isinstance(x, Number):
        assert x == y
    else:
        assert_arrays_equal(x, y)
         

def assert_arrays_equal(x, y):
    assert np.alltrue(x == y)


def create_spectrogram_axes(
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


def create_samples(shape, factor=100, dtype='int32'):
    arrays = [
        _create_samples_aux(shape, factor, dtype, i)
        for i in range(len(shape))]
    return sum(arrays)
    
    
def _create_samples_aux(shape, factor, dtype, i):
    n = len(shape)
    j = n - 1 - i
    m = shape[i]
    s = (factor ** j) * np.arange(m)
    s.shape = (m,) + (1,) * j
    return s