import datetime

from vesper.tests.test_case import TestCase
import vesper.ephem.ephem_utils as ephem_utils
import vesper.util.time_utils as time_utils


_LAT = 42.45
_LON = -76.3
_ONE_DAY = datetime.timedelta(days=1)


class EphemUtilsTests(TestCase):
    
    
    def test_memoization_bug_1(self):
        
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
        

    def test_memoization_bug_2(self):
        
        """
        Regression test for memoization bug discovered on 2017-07-26.
        
        The bug caused erroneous results when the memoization cache
        was full. This test gets a series of sunrise times whose length
        exceeds the cache size, and then gets the same series again
        for comparison.
        """
        
        start_date = datetime.date(2017, 7, 26)
        
        # This must exceed the memoization cache size (fixed at 100
        # items as of 2017-07-26) for this test to be effective.
        num_days = 101
        
        times_a = _get_sunrise_times(start_date, num_days)
        times_b = _get_sunrise_times(start_date, num_days)
        
        self.assertEqual(times_a, times_b)
        
        
def _get_sunrise_times(start_date, num_days):
    
    times = []
    date = start_date
    
    for _ in range(num_days):
        
        dt = ephem_utils.get_event_time('Sunrise', _LAT, _LON, date)
        times.append(dt)
        
        date += _ONE_DAY
        
    return times
