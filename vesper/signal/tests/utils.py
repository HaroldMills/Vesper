"""Utility functions and constants for signal class unit tests."""


from numbers import Number
import os.path
import random

import numpy as np


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


def test_indexing(x, expected, test_count):
     
    # Before random indexing, try indexing with a single colon.
    # This will elicit many possible bugs.
    assert_arrays_equal(x[:], expected[:], strict=True)
    
    shape = expected.shape
     
    if _any_zero(shape):
        return
     
    for _ in range(test_count):
         
        index_count = random.randrange(len(shape)) + 1
         
        if index_count == 1:
            key = _get_test_index(shape[0])
             
        else:
            key = tuple(_get_test_index(n) for n in shape[:index_count])
             
        # print(key, x[key], expected[key])
         
        assert_arrays_equal(x[key], expected[key], strict=True)

    
def _any_zero(x):
    return not np.all(np.array(x))


def _get_test_index(n):
    
    index_type = random.choice(('int', 'range', 'colon'))
    
    if index_type == 'int':
        return random.randrange(n)
    
    elif index_type == 'range':
        start = random.randrange(-n, n)
        stop = random.randrange(-n, n)
        return slice(start, stop)
    
    else:
        return slice(None)
    
    
# def test_mapping(a, forward_name, inverse_name, cases):
#      
#     for x, y in cases:
#          
#         method = getattr(a, forward_name)
#         result = method(x)
#         assert_numbers_or_arrays_equal(result, y)
#           
#         method = getattr(a, inverse_name)
#         result = method(y)
#         assert_numbers_or_arrays_equal(result, x)
         
         
def assert_numbers_or_arrays_equal(x, y):
    if isinstance(x, Number):
        assert x == y
    else:
        assert_arrays_equal(x, y)
         

def assert_arrays_equal(x, y, strict=False):
    if strict:
        assert x.dtype == y.dtype
    assert np.alltrue(x == y)


def create_samples(shape, factor=100, sample_type='int32'):
    arrays = [
        _create_samples_aux(shape, factor, sample_type, i)
        for i in range(len(shape))]
    return sum(arrays)
    
    
def _create_samples_aux(shape, factor, sample_type, i):
    n = len(shape)
    j = n - 1 - i
    m = shape[i]
    s = (factor ** j) * np.arange(m, dtype=sample_type)
    s.shape = (m,) + (1,) * j
    return s


def create_test_audio_file_path(file_name):
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, 'data', 'Audio Files', file_name)
