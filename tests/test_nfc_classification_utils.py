import numpy as np

import vesper.util.nfc_classification_utils as utils

from test_case import TestCase


class NfcDetectionUtilsTests(TestCase):
    
    
    def test_sum_adjacent(self):
        
        cases = [
            ((4, 6), (2, 3), [[24, 42], [96, 114]]),
            ((6, 4), (3, 2), [[27, 39], [99, 111]])
        ]
        
        for shape, block_size, expected in cases:
            x = np.arange(24)
            x.shape = shape
            x = utils._sum_adjacent(x, block_size)
            self._assert_arrays_equal(x, np.array(expected))
            