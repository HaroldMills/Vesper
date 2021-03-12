import numpy as np

from vesper.tests.test_case import TestCase
import vesper.util.signal_utils as signal_utils


class SignalUtilsTests(TestCase):
    
    
    def test_get_concatenated_signal_read_data(self):
        
        
        # empty concatenated signal
        
        bounds = [0]
        
        cases = [
            
            # empty read interval
            ((-100, -100), (0, 0, 0, 0)),
            ((0, 0), (0, 0, 0, 0)),
            ((100, 100), (0, 0, 0, 0)),
            ((100, 0), (0, 0, 0, 0)),
            
            # nonempty read interval
            ((-100, 100), (-1, -100, 0, 100)),
            ((-100, 0), (-1, -100, 0, 0)),
            ((0, 100), (0, 0, 0, 100)),
            ((100, 200), (0, 100, 0, 200)),
        
        ]
        
        self._test_get_concatenated_signal_read_data_aux(bounds, cases)
        
        
        # nonempty concatenated signal
        
        bounds = [0, 10, 30]
        
        cases = [
            
            # empty read interval
            ((-100, -100), (0, 0, 0, 0)),
            ((0, 0), (0, 0, 0, 0)),
            ((100, 100), (0, 0, 0, 0)),
            ((100, 0), (0, 0, 0, 0)),
            
            # nonempty read interval
            ((-100, 100), (-1, -100, 2, 70)),
            ((-100, 5), (-1, -100, 0, 5)),
            ((0, 5), (0, 0, 0, 5)),
            ((0, 10), (0, 0, 0, 10)),
            ((0, 11), (0, 0, 1, 1)),
            ((0, 20), (0, 0, 1, 10)),
            ((0, 30), (0, 0, 1, 20)),
            ((0, 31), (0, 0, 2, 1)),
            ((10, 15), (1, 0, 1, 5)),
            ((10, 30), (1, 0, 1, 20)),
            ((10, 31), (1, 0, 2, 1)),
            ((15, 40), (1, 5, 2, 10)),
            
        ]
        
        self._test_get_concatenated_signal_read_data_aux(bounds, cases)
    
    
    def _test_get_concatenated_signal_read_data_aux(self, bounds, cases):
        get_read_data = signal_utils.get_concatenated_signal_read_data
        for (start_index, end_index), expected in cases:
            actual = get_read_data(bounds, start_index, end_index)
            self.assertEqual(actual, expected)
    
    
    def test_get_concatenated_signal_index_data(self):
        
        
        # empty concatenated signal
        
        bounds = [0]
        
        cases = [
            (-100, (-1, -100)),
            (-2, (-1, -2)),
            (-1, (-1, -1)),
            (0, (0, 0)),
            (1, (0, 1)),
            (2, (0, 2)),
            (100, (0, 100)),
        ]
        
        self._test_get_concatenated_signal_index_data_aux(bounds, cases)
        
        
        # nonempty concatenated signal
        
        bounds = [0, 10, 30]
        
        cases = [
            (-100, (-1, -100)),
            (-2, (-1, -2)),
            (-1, (-1, -1)),
            (0, (0, 0)),
            (1, (0, 1)),
            (5, (0, 5)),
            (9, (0, 9)),
            (10, (1, 0)),
            (11, (1, 1)),
            (20, (1, 10)),
            (29, (1, 19)),
            (30, (2, 0)),
            (31, (2, 1)),
            (100, (2, 70)),
        ]
        
        self._test_get_concatenated_signal_index_data_aux(bounds, cases)
    
    
    def _test_get_concatenated_signal_index_data_aux(self, bounds, cases):
        get_index_data = signal_utils.get_concatenated_signal_index_data
        for index, expected in cases:
            actual = get_index_data(bounds, index)
            self.assertEqual(actual, expected)
    
    
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
