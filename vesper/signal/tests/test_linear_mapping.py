import numpy as np

from vesper.tests.test_case import TestCase

from ..linear_mapping import LinearMapping


class LinearMappingTests(TestCase):


    def test_init(self):
        
        incomplete_args_cases = [
            ((), (1, 0)),
            ((2,), (2, 0)),
        ]
        
        for args, expected in incomplete_args_cases:
            mapping = LinearMapping(*args)
            expected = LinearMapping(*expected)
            self.assertEqual(mapping, expected)
            
        keyword_args_cases = [
            ({'b': .5}, (1, .5))
        ]
        
        for kwargs, expected in keyword_args_cases:
            mapping = LinearMapping(**kwargs)
            expected = LinearMapping(*expected)
            self.assertEqual(mapping, expected)
            
            
    def test_eq(self):
        
        cases = [
            ((2, 1), (2, 1), True),
            ((2, 1), (2, 0), False),
            ((2, 1), (1, 1), False)
        ]
        
        for args0, args1, expected in cases:
            m0 = LinearMapping(*args0)
            m1 = LinearMapping(*args1)
            self.assertEqual(m0 == m1, expected)
            
            
    def test(self):
        
        m = LinearMapping(2, 1)
        
        self.assertEqual(m.a, 2)
        self.assertEqual(m.b, 1)
        
        self.assertEqual(m.map(0), 1)
        self.assertEqual(m.invert(0), -.5)
        
        cases = [
            ([], []),
            ([.25], [1.5]),
            ([0, 1], [1, 3])
        ]
        
        for x, y in cases:
            x = np.array(x)
            y = np.array(y)
            self.assertTrue(np.alltrue(m.map(x) == y))
            self.assertTrue(np.alltrue(m.invert(y) == x))
        
        
    def test_noninvertible_mapping(self):
        m = LinearMapping(0, 0)
        self._assert_raises(ZeroDivisionError, m.invert, 1)
        