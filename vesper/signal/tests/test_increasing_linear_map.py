import numpy as np

from vesper.signal.increasing_linear_map import IncreasingLinearMap
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class IncreasingLinearMapTests(TestCase):


    def test_init(self):
        
        incomplete_args_cases = [
            ((), (1, 0)),
            ((2,), (2, 0)),
        ]
        
        for args, expected in incomplete_args_cases:
            m = IncreasingLinearMap(*args)
            expected = IncreasingLinearMap(*expected)
            self.assertEqual(m, expected)
            
        keyword_args_cases = [
            ({'b': .5}, (1, .5))
        ]
        
        for kwargs, expected in keyword_args_cases:
            m = IncreasingLinearMap(**kwargs)
            expected = IncreasingLinearMap(*expected)
            self.assertEqual(m, expected)
            
            
    def test_eq(self):
        
        cases = [
            ((2, 1), (2, 1), True),
            ((2, 1), (2, 0), False),
            ((2, 1), (1, 1), False)
        ]
        
        for args0, args1, expected in cases:
            m0 = IncreasingLinearMap(*args0)
            m1 = IncreasingLinearMap(*args1)
            self.assertEqual(m0 == m1, expected)
            
            
    def test(self):
        
        m = IncreasingLinearMap(2, 1)
        
        self.assertEqual(m.a, 2)
        self.assertEqual(m.b, 1)
        
        self.assertEqual(m(0), 1)
        self.assertEqual(m.inverse(0), -.5)
        
        cases = [
            ([], []),
            ([.25], [1.5]),
            ([0, 1], [1, 3])
        ]
        
        for x, y in cases:
            x = np.array(x)
            y = np.array(y)
            utils.assert_arrays_equal(m(x), y)
            utils.assert_arrays_equal(m.inverse(y), x)
        
        
    def test_noninvertible_map(self):

        # zero slope
        self.assert_raises(ValueError, IncreasingLinearMap, 0, 0)

        # negative slope
        self.assert_raises(ValueError, IncreasingLinearMap, -1, 0)
