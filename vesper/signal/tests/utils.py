"""Utility functions and constants for signal class unit tests."""


from numbers import Number
import datetime
import os.path

import numpy as np

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_axis import ArrayAxis
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
    assert x.dtype == y.dtype
    assert np.alltrue(x == y)


def create_signal_axes(shape):
    
    if len(shape) == 0:
        shape = (0,)
        
    reference = Bunch(index=0, datetime=datetime.datetime.now())
    time_axis = TimeAxis(length=shape[0], reference_datetime=reference)
    
    lengths = shape[1:]
    n = len(lengths)
    array_axes = tuple(
        ArrayAxis(name='Axis ' + str(i), length=lengths[i]) for i in range(n))
    
    return (time_axis, array_axes, AmplitudeAxis())


def create_samples(shape, factor=100, dtype='int32'):
    arrays = [
        _create_samples_aux(shape, factor, dtype, i)
        for i in range(len(shape))]
    return sum(arrays)
    
    
def _create_samples_aux(shape, factor, dtype, i):
    n = len(shape)
    j = n - 1 - i
    m = shape[i]
    s = (factor ** j) * np.arange(m, dtype=dtype)
    s.shape = (m,) + (1,) * j
    return s


def create_test_audio_file_path(file_name):
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, 'data', 'Sound Files', file_name)
