import numpy as np

from vesper.tests.test_case import TestCase
import vesper.util.signal_utils as signal_utils


class SignalUtilsTests(TestCase):
    
    
    def test_find_samples(self):
        
        y = [2, 0, 1, 0, 1, 0, 2]
        
        cases = [
            
            # x in y
            ([0], y, [1, 3, 5]),
            ([2], y, [0, 6]),
            ([0, 1], y, [1, 3]),
            ([1, 0], y, [2, 4]),
            ([0, 1, 0], y, [1, 3]),
            ([1, 0, 1], y, [2]),
            ([1, 0, 1, 0], y, [2]),
            
            # x not in y
            ([3], y, []),
            ([0, 3], y, []),
            ([2, 3], y, []),
            ([2, 3, 4], y, [])
            
        ]
        
        for x, y, expected in cases:
            x = np.array(x)
            y = np.array(y)
            expected = np.array(expected)
            result = signal_utils.find_samples(x, y)
            self._assert_arrays_equal(result, expected)


    def test_tolerant_find_samples(self):
        
        y = [4, 0, 2, 0, 2, 0, 4]
        
        cases = [
            
            # x in y
            ([0], y, [1, 3, 5]),
            ([0, 2], y, [1, 3]),
            ([1], y, [1, 2, 3, 4, 5]),
            ([0, 1], y, [1, 3]),
            ([1, 1], y, [1, 2, 3, 4]),
            ([5, 1], y, [0]),
            ([1, 5], y, [5]),
            
            # x not in y
            ([6], y, []),
            ([4, 2], y, [])
            
        ]
        
        for x, y, expected in cases:
            x = np.array(x)
            y = np.array(y)
            expected = np.array(expected)
            result = signal_utils.find_samples(x, y, tolerance=1)
            self._assert_arrays_equal(result, expected)
            
            

    def test_find_peaks_with_no_min_value(self):
        
        cases = [
            
            # arrays without peaks
            ([], []),
            ([0], []),
            ([0, 1], []),
            ([0, 0, 0], []),
            ([1, 0, 1], []),
            ([0, 1, 1, 0], []),
              
            # arrays with peaks
            ([0, 1, 0], [1]),
            ([-10, -9, -10], [1]),
            ([0, 1, 0, 1, 1, 0, 1, 0], [1, 6]),
            ([0, 10, 0, 10, 20, 0, 10, 0], [1, 4, 6])
            
        ]
        
        for x, expected in cases:
            x = np.array(x)
            expected = np.array(expected)
            actual = signal_utils.find_peaks(x)
            self._assert_arrays_equal(actual, expected)
            
            
    def test_find_peaks_with_min_value(self):
        
        cases = [
            ([0, 2, 0], 1, [1]),
            ([0, 2, 0], 2, [1]),
            ([0, 2, 0], 3, []),
            ([0, 1, 0, 1, 2, 0, 2, 0], None, [1, 4, 6]),
            ([0, 1, 0, 1, 2, 0, 2, 0], 0, [1, 4, 6]),
            ([0, 1, 0, 1, 2, 0, 2, 0], 1, [1, 4, 6]),
            ([0, 1, 0, 1, 2, 0, 2, 0], 2, [4, 6]),
            ([0, 1, 0, 1, 2, 0, 2, 0], 3, [])
        ]
        
        for x, min_value, expected in cases:
            x = np.array(x)
            expected = np.array(expected)
            actual = signal_utils.find_peaks(x, min_value)
            self._assert_arrays_equal(actual, expected)


    def test_find_peaks_with_min_separation(self):
        
        cases = [
            ([0, 1, 0], 1, [1]),
            ([0, 1, 0, 1, 0], 2, [1, 3]),
            ([0, 1, 0, 1, 0], 2.000001, [1]),
            ([0, 1, 0, 1, 0, 0, 1, 0], 3, [1, 6])
        ]
        
        for x, min_separation, expected in cases:
            x = np.array(x)
            expected = np.array(expected)
            actual = signal_utils.find_peaks(x, min_separation=min_separation)
            self._assert_arrays_equal(actual, expected)
            
            
    def test_find_peaks_with_min_value_and_separation(self):
         
        cases = [
            ([0, 1, 0], 1, 1, [1]),
            ([0, 1, 0], 2, 1, []),
            ([0, 1, 0, 1, 0], 1, 2, [1, 3]),
            ([0, 1, 0, 2, 0], 2, 2, [3]),
            ([0, 1, 0, 1, 0], 1, 2.000001, [1]),
            ([0, 1, 0, 2, 0, 0, 2, 0], 1, 2, [1, 3, 6]),
            ([0, 1, 0, 2, 0, 0, 2, 0], 2, 2, [3, 6]),
            ([0, 1, 0, 2, 0, 0, 2, 0], 1, 3, [1, 6])
        ]
         
        for x, min_value, min_separation, expected in cases:
            x = np.array(x)
            expected = np.array(expected)
            actual = signal_utils.find_peaks(x, min_value, min_separation)
            self._assert_arrays_equal(actual, expected)
            

# The following is for the four-argument version of
# `signal_utils._remove_close_peaks`
#     def test_find_peaks_with_min_value_and_separation(self):
#         
#         cases = [
#             
#             ([0, 1, 0], 1, 1, [1]),
#             ([0, 1, 0], 2, 1, []),
#             ([0, 1, 0, 1, 0], 1, 2, [1, 3]),
#             ([0, 1, 0, 2, 0], 2, 2, [3]),
#             
#             # `min_value` of `None`, so only `min_separation` considered
#             ([0, 1, 0, 2, 0], None, 3, [1]),
#             
#             # `x` drops below `min_value` between two close peaks
#             ([0, 1, 0, 2, 0], 1, 3, [1, 3]),
#             
#             # `x` does not drop below `min_value` between two not-close peaks
#             ([0, 1, .5, 2, 0], .5, 2, [1, 3]),
#             
#             # `x` does not drop below `min_value` between two close peaks
#             ([0, 1, .5, 2, 0], .5, 3, [1]),
#             
#         ]
#         
#         for x, min_value, min_separation, expected in cases:
#             x = np.array(x)
#             expected = np.array(expected)
#             actual = signal_utils.find_peaks(x, min_value, min_separation)
#             self._assert_arrays_equal(actual, expected)
