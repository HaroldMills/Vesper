from vesper.tests.test_case import TestCase
import vesper.signal.signal_indexer as signal_indexer


# This module tests the auxiliary functions of the `signal_indexer`
# module, but not the `SignalIndexer` class. The `test_signal` module
# tests the `SignalIndexer` class as part of testing the `Signal` class.


NAME = 'time'


class SignalIndexerTests(TestCase):


    def test_normalize_int_key(self):
        
        n = 5
        
        cases = [
            (0, 0),
            (1, 1),
            (-1, n - 1),
            (-2, n - 2),
        ]
        
        for key, expected in cases:
            
            actual = signal_indexer._normalize_int_key(key, n, NAME)
            expected = slice(expected, expected + 1)
            self.assertEqual(actual, expected)
 


    def test_normalize_int_key_errors(self):
        
        n = 5
        
        cases = [
            (n, n),
            (-n - 1, n),
        ]
        
        for case in cases:
            args = case + (NAME,)
            self.assert_raises(
                IndexError, signal_indexer._normalize_int_key, *args)


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
            args = (slice(*args), n, NAME)
            actual = signal_indexer._normalize_slice_key(*args)
            expected = slice(*expected)
            self.assertEqual(actual, expected)
            
            
    def test_normalize_slice_key_errors(self):
        method = signal_indexer._normalize_slice_key
        key = slice(0, 5, 2)
        self.assert_raises(IndexError, method, key, 5, NAME)
        
        
    def test_normalize_key(self):
        
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
            
            if isinstance(key, int):
                expected = slice(key, key + 1), True

            else:
                key = slice(*key)
                expected = slice(*expected), False
                            
            actual = signal_indexer._normalize_key(key, n, NAME)
            self.assertEqual(actual, expected)
            
            
    def test_normalize_key_errors(self):
         
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
                args = (case,)
            else:
                args = (slice(*case),)
                
            args += (n, NAME)
            
            self.assert_raises(
                IndexError, signal_indexer._normalize_key, *args)
