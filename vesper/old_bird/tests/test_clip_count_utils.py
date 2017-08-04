import datetime

from vesper.tests.test_case import TestCase
import vesper.old_bird.clip_count_utils as clip_count_utils


_START_TIME = datetime.datetime(2017, 8, 3)
_10 = datetime.timedelta(seconds=10)
_16 = datetime.timedelta(seconds=16)


def _t(seconds):
    return _START_TIME + datetime.timedelta(seconds=seconds)
    
    
class ClipCountsExportUtilsTests(TestCase):


    def test_get_bird_count(self):
        
        cases = [
            
            ([], _10, 0),
            ([0], _10, 1),
            ([0, 1], _10, 1),
            ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], _10, 2),
            ([0, 5, 10, 15, 20, 25, 30, 35], _10, 4),
            ([0, 5, 10, 15, 20, 25, 30, 35], _16, 2)
            
        ]
        
        for times, interval, expected_count in cases:
            times = [_t(t) for t in times]
            count = clip_count_utils.get_bird_count(times, interval )
            self.assertEqual(count, expected_count)
