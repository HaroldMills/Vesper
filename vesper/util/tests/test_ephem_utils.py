import datetime

from vesper.tests.test_case import TestCase
from .. import ephem_utils
from .. import time_utils


_LAT = 42.45
_LON = -76.3


class EphemUtilsTests(TestCase):
    
    
    def test_memoization_bug(self):
        
        """
        Regression test for memoization bug discovered on 2016-04-14.
        
        The bug was introduced on 2016-03-29 in commit 7c84046. The
        bug caused the `memoize` function to omit the event string
        from the cache key tuple. Hence `memoize` function results
        were cached and retrieved by (lat, lon, date) rather than
        the correct (event, lat, lon, date). This test fails for
        the module with the bug but succeeds for one without it.
        """
        
        d = datetime.date
        dt = time_utils.create_utc_datetime
        
        cases = [
            ('Sunrise', d(2016, 4, 14), dt(2016, 4, 14, 10, 26)),
            ('Sunset', d(2016, 4, 14), dt(2016, 4, 14, 23, 47))
        ]
        
        for event, date, expected in cases:
            dt = ephem_utils.get_event_time(event, _LAT, _LON, date)
            dt = time_utils.round_datetime(dt, 60)
            self._assert_almost_equal(dt, expected)
            
            
    def _assert_almost_equal(self, a, b):
        diff = abs((a - b).total_seconds() / 60.)
        self.assertLessEqual(diff, 1)
        
