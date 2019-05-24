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
        
        
# The following was part of an interrupted effort to add new twilight
# period measurements to the `vesper.mpg_ranch.clips_csv_file_exporter`
# module. It is not complete, and should be replaced by new code when
# the `ephem_utils` module is overhauled to use Skyfield instead of
# PyEphem.
#     def test_get_daylight_period(self):
#          
#         # This method checks the daylight periods computed by the
#         # `ephem_utils.get_daylight_period` function using event
#         # times computed by `ephem_utils.get_event_time`.
#         # Unfortunately, this does not appear to be entirely reliable
#         # at higher latitudes, where we sometimes
#         locations = [
#             (42.45, -76.3),
#             (46.87, -113.99),
#         ]
#         
#         start_time = datetime.datetime(2010, 1, 1, tzinfo=pytz.utc)
#         end_time = datetime.datetime(2030, 1, 1, tzinfo=pytz.utc)
#          
#         num_times = 10000
#          
#         test_period_duration = (end_time - start_time).total_seconds()
#         offsets = np.random.uniform(0, test_period_duration, num_times)
#          
#         for lat, lon in locations:
#             
#             for offset in offsets:
#                  
#                 time = start_time + datetime.timedelta(seconds=offset)
#                 period = ephem_utils.get_daylight_period(lat, lon, time)
#                 expected_period = _get_expected_period(lat, lon, time)
#                 self.assertEqual(period, expected_period)
#                 
#                 
# _PERIOD_NAMES = {
#     'Astronomical Dawn': 'Astronomical Twilight',
#     'Nautical Dawn': 'Nautical Twilight',
#     'Civil Dawn': 'Civil Twilight',
#     'Sunrise': 'Day',
#     'Sunset': 'Civil Twilight',
#     'Civil Dusk': 'Nautical Twilight',
#     'Nautical Dusk': 'Astronomical Twilight',
#     'Astronomical Dusk': 'Night'
# }
# 
# _EVENT_NAMES = sorted(_PERIOD_NAMES.keys())
#         
# 
# def _get_expected_period(lat, lon, time):
#     
#     date = time.date()
#     prev_date = datetime.date.fromordinal(date.toordinal() - 1)
#     next_date = datetime.date.fromordinal(date.toordinal() + 1)
#     
#     events = \
#         _get_events(lat, lon, prev_date) + \
#         _get_events(lat, lon, date) + \
#         _get_events(lat, lon, next_date)
#         
#     if len(events) == 0:
#         return 'Not Found'
#         
#     event_times, event_names = list(zip(*events))
#     
#     i = bisect.bisect_right(event_times, time) - 1
#     
#     if i == -1 or i == len(event_times) - 1:
#         return 'Not Found'
#     else:
#         return _PERIOD_NAMES[event_names[i]] 
#     
#     
# def _get_events(lat, lon, date):
#     
#     events = [
#         (ephem_utils.get_event_time(name, lat, lon, date), name)
#         for name in _EVENT_NAMES]
#     
#     events = [e for e in events if e[0] is not None]
#     
#     events.sort()
#     
#     return events


def _get_sunrise_times(start_date, num_days):
    
    times = []
    date = start_date
    
    for _ in range(num_days):
        
        dt = ephem_utils.get_event_time('Sunrise', _LAT, _LON, date)
        times.append(dt)
        
        date += _ONE_DAY
        
    return times
