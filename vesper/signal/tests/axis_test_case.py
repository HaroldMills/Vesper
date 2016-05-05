"""Base class for axis unit test cases."""


from numbers import Number

import numpy as np

from vesper.tests.test_case import TestCase


class AxisTestCase(TestCase):
    
    
    def _test_init(self, args, defaults, cls, assert_function):
        
        for i in range(len(args)):
            some_args = args[:i]
            a = cls(*some_args)
            expected = args[:i] + defaults[i:]
            assert_function(a, *expected)
    
    
    def _test_eq(self, cls, args, changes):
        
        a = cls(*args)
        
        b = cls(*args)
        self.assertTrue(a == b)
        
        for i in range(len(changes)):
            changed_args = args[:i] + (changes[i],) + args[i + 1:]
            b = cls(*changed_args)
            self.assertFalse(a == b)


    def _test_mapping(self, a, forward_name, inverse_name, cases):
         
        for x, y in cases:
             
            method = getattr(a, forward_name)
            result = method(x)
            self._assert_equal(result, y)
              
            method = getattr(a, inverse_name)
            result = method(y)
            self._assert_equal(result, x)
             
             
    def _assert_equal(self, x, y):
        if isinstance(x, Number):
            self.assertEqual(x, y)
        else:
            self._assert_arrays_equal(x, y)
             
 
    def _assert_arrays_equal(self, x, y):
        self.assertTrue(np.alltrue(x == y))
