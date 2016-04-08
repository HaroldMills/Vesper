import numpy as np

from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
import vesper.util.nfc_detection_utils as utils


_PARAMS = Bunch(
    typical_background_percentile = 50,
    small_background_percentile = 10,
    bit_threshold_factor = 3,
    min_event_length = 5,
    max_event_length = 10,
    min_event_separation = 10,
    min_event_density = 80
)


class NfcDetectionUtilsTests(TestCase):
    
    
    def test_detect_simple(self):
        
        cases = (
                 
            # No events.
            ([], []),
            
            # Positives.
            ([(10, 15)], [(10, 15)]),
            ([(10, 17)], [(10, 17)]),
            ([(10, 20)], [(10, 20)]),
            ([(0, 5)], [(0, 5)]),
            ([(0, 10)], [(0, 10)]),
            ([(95, 100)], [(95, 100)]),
            ([(10, 20), (30, 40, 2)], [(10, 20), (30, 40)]),
            ([(10, 20), (30, 40), (50, 60)], [(10, 20), (30, 40), (50, 60)]),
            ([(10, 15, np.array([1, 1, 0, 1, 1]))], [(10, 15)]),
            ([(95, 100, np.array([1, 1, 1, 0, 1]))], [(95, 100)]),
             
            # Too short.
            ([(10, 14)], []),
            ([(0, 4)], []),
            ([(96, 99)], []),
            
            # Too long.
            ([(10, 21)], []),
            ([(0, 11)], []),
            ([(89, 100)], []),
            ([(0, 100)], []),
            ([(10, 15), (20, 25)], []),
            
            # Insufficient density.
            ([(10, 20, np.array([1, 1, 1, 1, 0, 0, 0, 1, 1, 1]))], [])
            
        )
        
        for spans, expected in cases:
            
            x = 4 + np.random.uniform(-.1, .1, 100)
            
            for span in spans:
                start_index, end_index = span[:2]
                height = 1 if len(span) == 2 else span[2]
                x[start_index:end_index] += height

            result, _ = utils._detect(x, _PARAMS)
            
            self.assertEqual(result, expected)
            