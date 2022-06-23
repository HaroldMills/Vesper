"""
Unit test test case mixin class.

This mixin class is intended for use with a subclass of either
`unittest.TestCase` or `django.test.TestCase`. It includes several
convenience `_assert...` methods.
"""


import vesper.util.numpy_utils as numpy_utils


class TestCaseMixin:
    
    
    def assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class as e:
            pass
            # print(str(e))
            
            
    def assert_arrays_equal(self, x, y):
        self.assertTrue(numpy_utils.arrays_equal(x, y))
        
        
    def assert_arrays_close(self, x, y):
        self.assertTrue(numpy_utils.arrays_close(x, y))
