"""Unit test test case superclass with custom `_assert_raises` method."""


import unittest

import vesper.util.numpy_utils as numpy_utils


class TestCase(unittest.TestCase):
    
    
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class as e:
            pass
            # print(str(e))
            
            
    def _assert_arrays_equal(self, x, y):
        self.assertTrue(numpy_utils.arrays_equal(x, y))
        
        
    def _assert_arrays_close(self, x, y):
        self.assertTrue(numpy_utils.arrays_close(x, y))
