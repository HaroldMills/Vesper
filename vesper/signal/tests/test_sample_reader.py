from vesper.tests.test_case import TestCase
import vesper.signal.sample_reader as sample_reader


# This module tests the auxiliary functions of the `sample_reader`
# module, but not the `SampleReader` class. The `test_signal` module
# tests the `SampleReader` class as part of testing the `Signal` class.


class SampleReaderTests(TestCase):


    def test_normalize_int_key(self):
        
        method = sample_reader._normalize_int_key
        
        n = 5
        
        cases = [
            (0, 0),
            (1, 1),
            (-1, n - 1),
            (-2, n - 2),
        ]
        
        for key, expected in cases:
            
            # Test without axis name arg.
            actual = method(key, n)
            self.assertEqual(actual, expected)
            
            # Test with axis name arg.
            actual = method(key, n, 'time')
            self.assertEqual(actual, expected)
 


    def test_normalize_int_key_errors(self):
        
        method = sample_reader._normalize_int_key
        
        n = 5
        
        cases = [
            (n, n),
            (-n - 1, n),
        ]
        
        for case in cases:
            
            # Test without axis name arg.
            self._assert_raises(IndexError, method, *case)
            
            # Test with axis name arg.
            args = case + ('time',)
            self._assert_raises(IndexError, method, *args)


    def test_normalize_slice_key(self):
        
        n = 5
        
        cases = [
            
            # nonnegative slice bounds
            ((0, 1), (0, 1)),
            ((0, 3), (0, 3)),
            ((2, 4), (2, 4)),
            
            # negative start
            ((-n, n), (0, n)),
            ((-n + 1, n), (1, n)),
            
            # negative stop
            ((0, -1), (0, n - 1)),
            ((0, -2), (0, n - 2)),
            
            # negative start and stop
            ((-n, -1), (0, n - 1)),

            # clipped start
            ((-n - 1, n), (0, n)),
            ((-n - 2, n), (0, n)),
            
            # clipped stop
            ((0, n + 1), (0, n)),
            ((0, n + 2), (0, n)),
            
            # clipped start and stop
            ((-n - 1, n + 1), (0, n)),
            
            # empty slices
            ((0, 0), (0, 0)),
            ((1, 1), (1, 1)),
            ((-1, -1), (n - 1, n - 1)),
            ((-n, -n), (0, 0)),
            ((0, -n), (0, 0)),
            ((0, -n - 1), (0, 0)),
            ((0, -n - 2), (0, 0)),
            ((2, 1), (2, 2)),
            ((2, 0), (2, 2)),
            ((n, 0), (n, n)),
            ((n, -1), (n, n)),
            ((n + 1, 0), (n, n)),

        ]
        
        for args, expected in cases:
            args = (slice(*args), n)
            actual = sample_reader._normalize_slice_key(*args)
            expected = slice(*expected)
            self.assertEqual(actual, expected)
            
            
    def test_normalize_slice_key_errors(self):
        method = sample_reader._normalize_slice_key
        key = slice(0, 5, 2)
        self._assert_raises(IndexError, method, key, 5)
        
        
    def test_normalize_int_or_slice_key(self):
        
        method = sample_reader._normalize_int_or_slice_key
            
        n = 5
        
        cases = [
            
            # integer key
            (0, 0),
            (1, 1),
            (n - 1, n - 1),
            
            # slice key
            ((0, 1), (0, 1)),
            ((1, 0), (1, 1)),
            ((0, -1), (0, n - 1)),
            
            
        ]
        
        for key, expected in cases:
            
            if isinstance(key, tuple):
                key = slice(*key)
                expected = slice(*expected)
                            
            # Test without axis name arg.
            actual = method(key, n)
            self.assertEqual(actual, expected)
            
            # Test with axis name arg.
            actual = method(key, n, 'time')
            self.assertEqual(actual, expected)
            
            
    def test_normalize_int_or_slice_key_errors(self):
         
        method = sample_reader._normalize_int_or_slice_key
        
        n = 5
         
        cases = [
             
            # integer key
            n,
            -n - 1,
             
            # slice key
            (0, n, 2),
            
        ]
         
        for case in cases:
            
            if isinstance(case, int):
                args = (case, n)
            else:
                args = (slice(*case), n)
                
            # Test without axis name arg.
            self._assert_raises(IndexError, method, *args)
            
            # Test with axis name arg.
            args += ('time',)
            self._assert_raises(IndexError, method, *args)
