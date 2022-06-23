import numpy as np

from vesper.tests.test_case import TestCase
import vesper.util.numpy_utils as numpy_utils


class NumPyUtilsTests(TestCase):
    
    
    def test_arrays_equal(self):
        
        cases = [
            
            # equal arrays
            ([], [], True),
            ([0], [0], True),
            ([0], [0.], True),
            ([1.2], [1.2], True),
            ([[1, 2], [3, 4]], [[1, 2], [3, 4]], True),
            
            # unequal arrays
            ([], [1], False),
            ([[], []], [], False),
            ([1, 2], [[1], [2]], False),
            ([0], [1e-50], False)
            
        ]
        
        for x, y, expected in cases:
            x = np.array(x)
            y = np.array(y)
            actual = numpy_utils.arrays_equal(x, y)
            self.assertEqual(actual, expected)
            
            
    def test_arrays_close(self):
        
        cases = [
            
            # close arrays
            ([], [], True),
            ([0], [0], True),
            ([0], [0.], True),
            ([1.2], [1.2], True),
            ([[1, 2], [3, 4]], [[1, 2], [3, 4]], True),
            ([0], [1e-8], True),
            
            # non-close arrays
            ([], [1], False),
            ([[], []], [], False),
            ([1, 2], [[1], [2]], False),
            ([0], [.999999e-7], False)
            
            
        ]
        
        for x, y, expected in cases:
            x = np.array(x)
            y = np.array(y)
            actual = numpy_utils.arrays_close(x, y)
            self.assertEqual(actual, expected)
            
        
    def test_reproducible_choice(self):
        
        choice = numpy_utils.reproducible_choice
        
        ns = [10, 20]
        
        for n in ns:
            for size in range(n + 1):
                for replace in [True, False]:
                    x = np.arange(n)
                    a = choice(x, size, replace)
                    b = choice(x, size, replace)
                    self.assert_arrays_equal(a, b)
                    
                    
    def test_reproducible_permutation(self):
        
        permutation = numpy_utils.reproducible_permutation
        
        # integer argument
        for n in range(10):
            a = permutation(n)
            b = permutation(n)
            self.assert_arrays_equal(a, b)
            
        # array argument
        ns = [10, 20]
        for n in ns:
            x = np.arange(n)
            a = permutation(x)
            b = permutation(x)
            self.assert_arrays_equal(a, b)
            
            
    def test_reproducible_shuffle(self):
        
        shuffle = numpy_utils.reproducible_shuffle
        
        ns = [10, 20]
        
        for n in ns:
            
            x = np.arange(n)
            shuffle(x)
            
            y = np.arange(n)
            shuffle(y)
            
            self.assert_arrays_equal(x, y)
