"""Unit test test case superclass with custom `_assert_raises` method."""


import unittest


class TestCase(unittest.TestCase):
    
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class, e:
            print(str(e))
