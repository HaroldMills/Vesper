import unittest

from vesper.ui.clip_times_rug_plot import _find_page_num as find_page_num


class ClipTimesRugPlotTests(unittest.TestCase):
    
    
    def test_find_page(self):
        
        boundary_times = [float(t) for t in xrange(3)]
        
        cases = [
            (-.0001, None),
            (0., 0),
            (.5, 0),
            (.9999, 0),
            (1., 1),
            (1.5, 1),
            (2., 1),
            (2.0001, None)
        ]
        
        for time, expected_page_num in cases:
            page_num = find_page_num(time, boundary_times)
            self.assertEqual(expected_page_num, page_num)
