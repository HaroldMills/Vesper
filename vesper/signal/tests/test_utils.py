import unittest

import numpy as np

import vesper.signal.tests.utils as utils


class UtilsTests(unittest.TestCase):
    
    
    def test_create_samples(self):
        
        cases = [
                 
            ((), []),
            
            ((2,), [0, 1]),
            
            ((2, 3, 4), [
                [[0, 1, 2, 3],
                 [100, 101, 102, 103],
                 [200, 201, 202, 203]],
                                 
                [[10000, 10001, 10002, 10003],
                 [10100, 10101, 10102, 10103],
                 [10200, 10201, 10202, 10203]]
             ])
            
        ]
        
        for shape, expected in cases:
            samples = utils.create_samples(shape)
            expected = np.array(expected)
            utils.assert_arrays_equal(samples, expected)
        