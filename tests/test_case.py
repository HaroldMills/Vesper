"""Unit test test case superclass with custom `_assert_raises` method."""


import unittest

import numpy as np


class TestCase(unittest.TestCase):
    
    
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class as e:
            print(str(e))
            
            
    def _assert_arrays_equal(self, x, y):
        self.assertTrue(np.all(x == y))
