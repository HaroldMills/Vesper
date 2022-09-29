"""
Unit test test case mixin class.

This mixin class is intended for use with a subclass of either
`unittest.TestCase` or `django.test.TestCase`. It includes several
convenience `_assert...` methods.
"""


import vesper.util.numpy_utils as numpy_utils


SHOW_EXCEPTION_MESSAGES = False

class TestCaseMixin:
    
    
    def assert_raises(self, exception_class, function, *args, **kwargs):
        
        try:
            function(*args, **kwargs)

        except exception_class as e:
            if SHOW_EXCEPTION_MESSAGES:
                print(str(e))
                
        else:
            raise AssertionError(
                f'{exception_class.__name__} not raised by '
                f'{function.__name__}')
           
            
    async def assert_raises_async(
            self, exception_class, function, *args, **kwargs):

        try:
            await function(*args, **kwargs)

        except exception_class as e:
            if SHOW_EXCEPTION_MESSAGES:
                print(str(e))

        else:
            raise AssertionError(
                f'{exception_class.__name__} not raised by '
                f'{function.__name__}')


    def assert_arrays_equal(self, x, y):
        self.assertTrue(numpy_utils.arrays_equal(x, y))
        
        
    def assert_arrays_close(self, x, y):
        self.assertTrue(numpy_utils.arrays_close(x, y))
