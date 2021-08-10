"""
`sun_moon` module unit tests.

Note that the related `test_skyfield` script uses the `SunMoon` class
to test the `skyfield` package against USNO data much more extensively
than this module. That script takes much longer to run than the tests
of this module, however.
"""


from datetime import (
    date as Date,
    datetime as DateTime,
    timedelta as TimeDelta)

import pytz

from vesper.tests.test_case import TestCase
from vesper.ephem.sun_moon import Event, Position, SunMoon, SunMoonCache


# TODO: When the USNO web site is up again (as of 2020-12 it has been
# down for months, since it is "undergoing modernization efforts"), get
# more (and perhaps more accurate) solar and lunar position and
# illumination test data from it.

# TODO: Should we be using the USNO's NOVAS software for anything,
# for example for generating test data? There is a pip-installable
# Python wrapper for NOVAS available from PyPI.


# Ithaca, NY location and time zone.
TEST_LAT = 42.431964
TEST_LON = -76.501656
TEST_ELEVATION = 0
TEST_TIME_ZONE_NAME = 'US/Eastern'
TEST_TIME_ZONE = pytz.timezone(TEST_TIME_ZONE_NAME)
TEST_DATE = Date(2020, 10, 1)


def _events(*args):
    return [Event(*arg) for arg in args]


def _utc(*args):
    local_time = _get_localized_time(*args)
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time


def _get_localized_time(*args):
    naive_time = DateTime(*args)
    return TEST_TIME_ZONE.localize(naive_time)


def _round_time_to_nearest_minute(t):
    floor = t.replace(second=0, microsecond=0)
    delta = t - floor
    if delta.total_seconds() < 30:
        return floor
    else:
        return floor + TimeDelta(seconds=60)


SOLAR_POSITIONS = [
    (_utc(2020, 1, 1, 0), (-70.51, 353.67, 147103121)),
    (_utc(2021, 2, 1, 2), (-56.78, 47.77, 147410473)),
    (_utc(2022, 3, 1, 4), (-30.28, 70.88, 148224283)),
    (_utc(2023, 4, 1, 6), (-9.75, 74.69, 149473176)),
    (_utc(2024, 5, 1, 8), (20.73, 87.87, 150747972)),
    (_utc(2025, 6, 1, 10), (46.85, 103.21, 151703723)),
    (_utc(2026, 7, 1, 12), (65.80, 137.62, 152090988)),
    (_utc(2027, 8, 1, 14), (63.49, 206.09, 151837501)),
    (_utc(2028, 9, 1, 16), (38.48, 240.68, 150948366)),
    (_utc(2029, 10, 1, 18), (7.83, 257.93, 149749701)),
    (_utc(2030, 11, 1, 20), (-22.82, 270.65, 148464087)),
    (_utc(2031, 12, 1, 22), (-58.42, 301.27, 147509001)),
]
"""Solar position test data, obtained from suncalc.org on 2020-11-02."""

SOLAR_EVENTS = _events(
    (_utc(2020, 10, 1, 0, 55), 'Solar Midnight'),
    (_utc(2020, 10, 1, 5, 30), 'Astronomical Dawn'),
    (_utc(2020, 10, 1, 6, 3), 'Nautical Dawn'),
    (_utc(2020, 10, 1, 6, 36), 'Civil Dawn'),
    (_utc(2020, 10, 1, 7, 4), 'Sunrise'),
    (_utc(2020, 10, 1, 12, 55), 'Solar Noon'),
    (_utc(2020, 10, 1, 18, 47), 'Sunset'),
    (_utc(2020, 10, 1, 19, 15), 'Civil Dusk'),
    (_utc(2020, 10, 1, 19, 47), 'Nautical Dusk'),
    (_utc(2020, 10, 1, 20, 20), 'Astronomical Dusk'),
    (_utc(2020, 10, 2, 0, 55), 'Solar Midnight'),
    (_utc(2020, 10, 2, 5, 31), 'Astronomical Dawn'),
    (_utc(2020, 10, 2, 6, 4), 'Nautical Dawn'),
    (_utc(2020, 10, 2, 6, 37), 'Civil Dawn'),
    (_utc(2020, 10, 2, 7, 5), 'Sunrise'),
    (_utc(2020, 10, 2, 12, 55), 'Solar Noon'),
)
"""Expected `get_solar_events_in_interval` events."""

SOLAR_EVENTS_IN_INTERVAL_DURATION = TimeDelta(hours=38)
"""`get_solar_events_in_interval` test interval duration."""

DAY_SOLAR_EVENTS = SOLAR_EVENTS[:10]
"""Expected `get_solar_events` day events."""

NIGHT_SOLAR_EVENTS = SOLAR_EVENTS[5:-1]
"""Expected `get_solar_events` day events."""

SOLAR_NOONS = [
    (Date(2020, 1, 1), _utc(2020, 1, 1, 12, 9)),
    (Date(2021, 2, 1), _utc(2021, 2, 1, 12, 19)),
    (Date(2022, 3, 1), _utc(2022, 3, 1, 12, 18)),
    (Date(2023, 4, 1), _utc(2023, 4, 1, 13, 9)),
    (Date(2024, 5, 1), _utc(2024, 5, 1, 13, 3)),
    (Date(2025, 6, 1), _utc(2025, 6, 1, 13, 3)),
    (Date(2026, 7, 1), _utc(2026, 7, 1, 13, 9)),
    (Date(2027, 8, 1), _utc(2027, 8, 1, 13, 12)),
    (Date(2028, 9, 1), _utc(2028, 9, 1, 13, 5)),
    (Date(2029, 10, 1), _utc(2029, 10, 1, 12, 55)),
    (Date(2030, 11, 1), _utc(2030, 11, 1, 12, 49)),
    (Date(2031, 12, 1), _utc(2031, 12, 1, 11, 55)),
]
"""Solar noon test data, obtained from timeanddate.com on 2021-01-04."""

SOLAR_MIDNIGHTS = [
    (Date(2020, 1, 2), _utc(2020, 1, 2, 0, 9)),
    (Date(2021, 2, 2), _utc(2021, 2, 2, 0, 19)),
    (Date(2022, 3, 2), _utc(2022, 3, 2, 0, 18)),
    (Date(2023, 4, 2), _utc(2023, 4, 2, 1, 9)),
    (Date(2024, 5, 2), _utc(2024, 5, 2, 1, 2)),
    (Date(2025, 6, 2), _utc(2025, 6, 2, 1, 4)),
    (Date(2026, 7, 2), _utc(2026, 7, 2, 1, 10)),
    (Date(2027, 8, 2), _utc(2027, 8, 2, 1, 12)),
    (Date(2028, 9, 2), _utc(2028, 9, 2, 1, 5)),
    (Date(2029, 10, 2), _utc(2029, 10, 2, 0, 55)),
    (Date(2030, 11, 2), _utc(2030, 11, 2, 0, 49)),
    (Date(2031, 12, 2), _utc(2031, 12, 1, 23, 55)),
]
"""Solar midnight test data, obtained from timeanddate.com on 2021-01-04."""

SOLAR_PERIODS = [
    (_utc(2020, 10, 1, 5, 25), 'Night'),
    (_utc(2020, 10, 1, 5, 35), 'Morning Astronomical Twilight'),
    (_utc(2020, 10, 1, 5, 58), 'Morning Astronomical Twilight'),
    (_utc(2020, 10, 1, 6, 8), 'Morning Nautical Twilight'),
    (_utc(2020, 10, 1, 6, 31), 'Morning Nautical Twilight'),
    (_utc(2020, 10, 1, 6, 41), 'Morning Civil Twilight'),
    (_utc(2020, 10, 1, 6, 59), 'Morning Civil Twilight'),
    (_utc(2020, 10, 1, 7, 9), 'Day'),
    (_utc(2020, 10, 1, 18, 42), 'Day'),
    (_utc(2020, 10, 1, 18, 52), 'Evening Civil Twilight'),
    (_utc(2020, 10, 1, 19, 10), 'Evening Civil Twilight'),
    (_utc(2020, 10, 1, 19, 20), 'Evening Nautical Twilight'),
    (_utc(2020, 10, 1, 19, 42), 'Evening Nautical Twilight'),
    (_utc(2020, 10, 1, 19, 52), 'Evening Astronomical Twilight'),
    (_utc(2020, 10, 1, 20, 15), 'Evening Astronomical Twilight'),
    (_utc(2020, 10, 1, 20, 25), 'Night'),
]
"""Solar period data, derived from the event data above."""

LUNAR_DATA = [
    (_utc(2020, 1, 1, 15, 46), (36.45, 151.09, 404551, .377)),
    (_utc(2021, 2, 1, 15, 46), (-45.98, .41, 371142, .806)),
    (_utc(2022, 3, 1, 15, 46), (8.22, 238.10, 372082, .012)),
    (_utc(2023, 4, 1, 15, 46), (7.09, 71.76, 403880, .825)),
    (_utc(2024, 5, 1, 15, 46), (-36.17, 274.30, 372332, .462)),
    (_utc(2025, 6, 1, 15, 46), (46.36, 117.75, 388663, .368)),
    (_utc(2026, 7, 1, 15, 46), (-66.08, 40.92, 402120, .969)),
    (_utc(2027, 8, 1, 15, 46), (44.69, 256.23, 357556, .006)),
    (_utc(2028, 9, 1, 15, 46), (-29.70, 82.53, 403409, .958)),
    (_utc(2029, 10, 1, 15, 46), (-7.22, 304.71, 387778, .405)),
    (_utc(2030, 11, 1, 15, 46), (19.73, 137.72, 372843, .426)),
    (_utc(2031, 12, 1, 15, 46), (-26.11, 24.15, 403198, .921)),
]
"""
Lunar position and illumination test data, obtained from suncalc.org
on 2020-11-02.
"""

LUNAR_POSITIONS = [(time, d[:3]) for time, d in LUNAR_DATA]

LUNAR_ILLUMINATIONS = [(time, d[3]) for time, d in LUNAR_DATA]

# The following were set to the minimum values with two significant digits
# that were required for tests involving suncalc.org and mooncalc.org test
# data to pass. Hopefully the larger thresholds can be reduced when the
# USNO web site is up again and we can obtain more and hopefully more
# accurate test data from it.
SOLAR_ALT_AZ_ERROR_THRESHOLD = .19
SOLAR_DISTANCE_ERROR_THRESHOLD = .00012
LUNAR_ALT_AZ_ERROR_THRESHOLD = .14
LUNAR_DISTANCE_ERROR_THRESHOLD = .015
LUNAR_ILLUMINATION_ERROR_THRESHOLD = .070

TIME_DIFFERENCE_ERROR_THRESHOLD = 60   # seconds

ONE_DAY = TimeDelta(days=1)


class SunMoonTests(TestCase):
    
    """Tests a `SunMoon` that yields UTC result times."""
    
    
    RESULT_TIMES_LOCAL = False
    
    
    def setUp(self):
        self.sun_moon = SunMoon(
            TEST_LAT, TEST_LON, TEST_TIME_ZONE, self.RESULT_TIMES_LOCAL)
    
    
    def test_initializer(self):
        
        rtl = self.RESULT_TIMES_LOCAL
        locn = (TEST_LAT, TEST_LON, TEST_TIME_ZONE_NAME)
        locn_rtl = locn + (rtl,)
        loc = (TEST_LAT, TEST_LON, TEST_TIME_ZONE)
        loc_rtl = loc + (rtl,)
        
        cases = [
            
            (locn, {}, loc + (False,)),
            (locn_rtl, {}, loc_rtl),
            (locn, {'result_times_local': rtl}, loc_rtl),
            
            (loc, {}, loc + (False,)),
            (loc_rtl, {}, loc_rtl),
            (loc, {'result_times_local': rtl}, loc_rtl),
            
        ]
        
        for args, kwargs, expected in cases:
            actual = SunMoon(*args, **kwargs)
            self._assert_sun_moon(actual, *expected)
    
    
    def _assert_sun_moon(
            self, sun_moon, latitude, longitude, time_zone,
            result_times_local):
        
        self.assertEqual(sun_moon.latitude, latitude)
        self.assertEqual(sun_moon.longitude, longitude)
        self.assertEqual(sun_moon.time_zone, time_zone)
        self.assertEqual(sun_moon.result_times_local, result_times_local)
    
    
    def test_get_scalar_solar_position(self):
        
        # Get positions twice to test caching to some extent.
        self._test_get_scalar_solar_position()
        self._test_get_scalar_solar_position()
    
    
    def _test_get_scalar_solar_position(self):
        return self._test_get_scalar_position(
            self.sun_moon.get_solar_position, SOLAR_POSITIONS,
            SOLAR_ALT_AZ_ERROR_THRESHOLD, SOLAR_DISTANCE_ERROR_THRESHOLD)
    
    
    def _test_get_scalar_position(
            self, method, expected_positions, alt_az_error_threshold,
            distance_error_threshold):
        
        for time, expected_pos in expected_positions:
            
            pos = method(time)
            
            self._check_pos(
                pos, expected_pos, alt_az_error_threshold,
                distance_error_threshold)
    
    
    def _check_pos(
            self, pos, expected_pos, alt_az_error_threshold,
            distance_error_threshold):
        
        alt, az, d = pos
        x_alt, x_az, x_d = expected_pos
        
        self._check_absolute_error(alt, x_alt, alt_az_error_threshold)
        self._check_absolute_error(az, x_az, alt_az_error_threshold)
        self._check_relative_error(d, x_d, distance_error_threshold)
    
    
    def _check_absolute_error(self, a, b, error_threshold):
        error = abs(a - b)
        # print(f'{name} {a} {b} {error}')
        self.assertLess(error, error_threshold)
    
    
    def _check_relative_error(self, a, b, error_threshold):
        error = abs((a - b) / b)
        # print(f'{name} {a} {b} {error}')
        self.assertLess(error, error_threshold)
    
    
    def test_get_vector_solar_position(self):
        self._test_get_vector_position(
            self.sun_moon.get_solar_position, SOLAR_POSITIONS,
            SOLAR_ALT_AZ_ERROR_THRESHOLD, SOLAR_DISTANCE_ERROR_THRESHOLD)
    
    
    def _test_get_vector_position(
            self, method, expected_positions, alt_az_error_threshold,
            distance_error_threshold):
        
        times, expected_positions = list(zip(*expected_positions))
        
        p = method(times)
 
        for i, expected in enumerate(expected_positions):
            actual = Position(p.altitude[i], p.azimuth[i], p.distance[i])
            self._check_pos(
                actual, expected, alt_az_error_threshold,
                distance_error_threshold)
    
    
    def test_get_solar_events_in_interval(self):
        
        d = TEST_DATE
        start_time = _get_localized_time(d.year, d.month, d.day)
        end_time = start_time + SOLAR_EVENTS_IN_INTERVAL_DURATION
        get_events = self.sun_moon.get_solar_events_in_interval
        
        # Test with no name filter.
        actual = get_events(start_time, end_time)
        self._check_events(actual, SOLAR_EVENTS)
    
        name_filters = (
            None,
            'Solar Midnight',
            'Sunrise',
            ('Sunrise', 'Sunset'),
            ('Civil Dawn', 'Solar Noon', 'Civil Dusk'),
        )
        
        # Test with name filter.
        for name_filter in name_filters:
            actual = get_events(start_time, end_time, name_filter)
            expected = self._get_expected_events(SOLAR_EVENTS, name_filter)
            self._check_events(actual, expected)
    
    
    def _get_expected_events(self, events, name_filter):
        
        if name_filter is None:
            return events
        
        elif isinstance(name_filter, str):
            return [e for e in events if e.name == name_filter]
        
        else:
            names = frozenset(name_filter)
            return [e for e in events if e.name in names]
    
    
    def _check_events(self, actual_events, expected_events):
         
        self.assertEqual(len(actual_events), len(expected_events))
         
        for i, (actual_time, actual_name) in enumerate(actual_events):
            self._assert_result_time_zone(actual_time)
            expected_time, expected_name = expected_events[i]
            self._assert_datetimes_nearly_equal(actual_time, expected_time)
            self.assertEqual(actual_name, expected_name)
    
    
    def _assert_result_time_zone(self, time):
        if self.RESULT_TIMES_LOCAL:
            self.assertEqual(time.tzinfo.zone, TEST_TIME_ZONE_NAME)
        else:
            self.assertEqual(time.tzname(), 'UTC')
    
    
    def _assert_datetimes_nearly_equal(self, a, b):
        delta = abs((a - b).total_seconds())
        self.assertLessEqual(delta, TIME_DIFFERENCE_ERROR_THRESHOLD)
    
    
    def test_get_solar_date(self):
        
        # Epsilon must be larger than we might like since test data
        # are rounded to nearest minute.
        epsilon = TimeDelta(minutes=2)
        
        test = self._test_get_scalar_solar_date
        
        for date, midnight in SOLAR_MIDNIGHTS:
            
            # A little before midnight is on previous day and night.
            test(midnight, -epsilon, date, -1, -1)
            
            # A little after midnight is on current day but previous night.
            test(midnight, epsilon, date, 0, -1)
        
        for date, noon in SOLAR_NOONS:
            
            # A little before noon is on current day but previous night.
            test(noon, -epsilon, date, 0, -1)
            
            # A little after noon is on current day and night.
            test(noon, epsilon, date, 0, 0)
        
        # Vector versions of above scalar tests
        test = self._test_get_vector_solar_date
        test(SOLAR_MIDNIGHTS, -epsilon, -1, -1)
        test(SOLAR_MIDNIGHTS, epsilon, 0, -1)
        test(SOLAR_NOONS, -epsilon, 0, -1)
        test(SOLAR_NOONS, epsilon, 0, 0)
    
    
    def _test_get_scalar_solar_date(
            self, time, time_delta, date, day_delta, night_delta):
        
        get_solar_date = self.sun_moon.get_solar_date
        assert_equal = self.assertEqual
        
        time = time + time_delta
        day_date = date + TimeDelta(days=day_delta)
        night_date = date + TimeDelta(days=night_delta)
        
        # day with implicit `day` argument
        date = get_solar_date(time)
        assert_equal(date, day_date)
        
        # day wth explicit `day` argument
        date = get_solar_date(time, day=True)
        assert_equal(date, day_date)
        
        # night
        date = get_solar_date(time, day=False)
        assert_equal(date, night_date)
    
    
    def _test_get_vector_solar_date(
            self, data, time_delta, day_delta, night_delta):
        
        get_solar_date = self.sun_moon.get_solar_date
        assert_equal = self.assertEqual

        dates, times = list(zip(*data))
        
        times = [time + time_delta for time in times]
        day_dates = [date + TimeDelta(days=day_delta) for date in dates]
        night_dates = [date + TimeDelta(days=night_delta) for date in dates]
        
        # day with implicit `day` argument
        dates = get_solar_date(times)
        assert_equal(dates, day_dates)
        
        # day wth explicit `day` argument
        dates = get_solar_date(times, day=True)
        assert_equal(dates, day_dates)
        
        # night
        dates = get_solar_date(times, day=False)
        assert_equal(dates, night_dates)
 
       
    def test_get_solar_events(self):
        
        cases = (
            ({}, DAY_SOLAR_EVENTS),
            ({'day': True}, DAY_SOLAR_EVENTS),
            ({'day': False}, NIGHT_SOLAR_EVENTS),
        )
        
        get_events = self.sun_moon.get_solar_events
        
        # Test with no name filter.
        for kwargs, expected in cases:
            actual = get_events(TEST_DATE, **kwargs)
            self._check_events(actual, expected)
        
        name_filters = (
            None,
            'Solar Midnight',
            'Sunrise',
            ('Sunrise', 'Sunset'),
            ('Civil Dawn', 'Solar Noon', 'Civil Dusk'),
        )
        
        # Test with name filter.
        for kwargs, events in cases:
            for name_filter in name_filters:
                actual = get_events(TEST_DATE, name_filter, **kwargs)
                expected = self._get_expected_events(events, name_filter)
                self._check_events(actual, expected)
    
    
    def _show_events(self, events, heading):
        print(heading + ':')
        for time, name in events:
            print(time, name)
    
    
    def test_get_solar_event_time(self):
        
        cases = (
            ({}, DAY_SOLAR_EVENTS),
            ({'day': True}, DAY_SOLAR_EVENTS),
            ({'day': False}, NIGHT_SOLAR_EVENTS),
        )
        
        for kwargs, expected in cases:
            for expected_time, event_name in expected:
                actual_time = self.sun_moon.get_solar_event_time(
                    TEST_DATE, event_name, **kwargs)
                self._assert_datetimes_nearly_equal(actual_time, expected_time)
    
    
    def test_solar_noons(self):
        self._test_get_solar_noon_or_midnight(SOLAR_NOONS, 'Solar Noon')
    
    
    def _test_get_solar_noon_or_midnight(self, cases, event_name):
        for date, expected in cases:
            time = self.sun_moon.get_solar_event_time(date, event_name)
            actual = _round_time_to_nearest_minute(time)
            self._assert_datetimes_nearly_equal(actual, expected)
    
    
    def test_solar_midnights(self):
        self._test_get_solar_noon_or_midnight(
            SOLAR_MIDNIGHTS, 'Solar Midnight')
    
    
    def test_get_scalar_solar_period_name(self):
        for time, expected in SOLAR_PERIODS:
            actual = self.sun_moon.get_solar_period_name(time)
            self.assertEqual(actual, expected)
    
    
    def test_get_vector_solar_period_name(self):
        times, expected_names = list(zip(*SOLAR_PERIODS))
        actual_names = self.sun_moon.get_solar_period_name(times)
        self.assertEqual(len(actual_names), len(expected_names))
        for actual, expected in zip(actual_names, expected_names):
            self.assertEqual(actual, expected)
        
        
    def test_get_lunar_position(self):
        
        # Get positions twice to test caching to some extent.
        self._test_get_scalar_lunar_position()
        self._test_get_scalar_lunar_position()
    
    
    def _test_get_scalar_lunar_position(self):
        return self._test_get_scalar_position(
            self.sun_moon.get_lunar_position, LUNAR_POSITIONS,
            LUNAR_ALT_AZ_ERROR_THRESHOLD, LUNAR_DISTANCE_ERROR_THRESHOLD)
    
    
    def test_get_vector_lunar_position(self):
        self._test_get_vector_position(
            self.sun_moon.get_lunar_position, LUNAR_POSITIONS,
            LUNAR_ALT_AZ_ERROR_THRESHOLD, LUNAR_DISTANCE_ERROR_THRESHOLD)
    
    
    def test_get_scalar_lunar_illumination(self):
        for time, expected_illumination in LUNAR_ILLUMINATIONS:
            illumination = self.sun_moon.get_lunar_illumination(time)
            self._check_relative_error(
                illumination, expected_illumination,
                LUNAR_ILLUMINATION_ERROR_THRESHOLD)
    
    
    def test_get_vector_lunar_illumination(self):
        
        times, expected_illuminations = list(zip(*LUNAR_ILLUMINATIONS))
        
        actual_illuminations = self.sun_moon.get_lunar_illumination(times)
        
        self.assertEqual(
            len(actual_illuminations), len(expected_illuminations))
        
        for actual, expected in \
                zip(actual_illuminations, expected_illuminations):
            
            self._check_relative_error(
                actual, expected, LUNAR_ILLUMINATION_ERROR_THRESHOLD)
    
    
    def test_naive_datetime_errors(self):
        
        sm = self.sun_moon
        
        # Methods that accept a single `datetime` argument.
        time = DateTime(2020, 10, 1)
        self._assert_raises(ValueError, sm.get_solar_position, time)
        self._assert_raises(ValueError, sm.get_solar_period_name, time)
        self._assert_raises(ValueError, sm.get_lunar_position, time)
        self._assert_raises(ValueError, sm.get_lunar_illumination, time)
        
        # `get_solar_events_in_interval` with first `datetime` naive.
        time1 = DateTime(2020, 10, 1)
        time2 = _get_localized_time(2020, 10, 2)
        self._assert_raises(
            ValueError, sm.get_solar_events_in_interval, time1, time2)
        
        # `get_solar_events_in_interval` with second `datetime` naive.
        time1 = _get_localized_time(2020, 10, 1)
        time2 = DateTime(2020, 10, 2)
        self._assert_raises(
            ValueError, sm.get_solar_events_in_interval, time1, time2)
    
    
    def test_that_some_polar_functions_do_not_raise_exceptions(self):
        
        # TODO: If we set `time_2` to any day past 2020-01-10,
        # `get_solar_events_in_interval` seems to hang. Why?
        
        polar_latitudes = [-90, 90]
        time_1 = _get_localized_time(2020, 1, 1)
        time_2 = _get_localized_time(2020, 1, 10)
        
        for latitude in polar_latitudes:
            
            sm = SunMoon(latitude, TEST_LON, TEST_TIME_ZONE_NAME)
            
            cases = (
                (sm.get_solar_position, time_1),
                (sm.get_solar_events_in_interval, time_1, time_2),
                (sm.get_lunar_position, time_1),
                (sm.get_lunar_illumination, time_1)
            )
            
            for case in cases:
                method = case[0]
                args = case[1:]
                method(*args)
    
    
    def test_polar_errors(self):
        
        polar_latitudes = [-90, 90]
        date = Date(2020, 1, 1)
        time = _get_localized_time(2020, 1, 1)
        
        for latitude in polar_latitudes:
            
            sm = SunMoon(latitude, TEST_LON, TEST_TIME_ZONE_NAME)
            
            cases = (
                (sm.get_solar_events, date),
                (sm.get_solar_event_time, date, 'Sunrise'),
                (sm.get_solar_period_name, time),
            )
            
            for case in cases:
                self._assert_raises(ValueError, *case)
    
    
    def test_solar_event_time_altitudes(self):
         
        expected_altitudes = {
            'Ast': -18,
            'Nau': -12,
            'Civ': -6,
            'Sun': -.8333,
        }
         
        sm = SunMoon(
            TEST_LAT, TEST_LON, TEST_TIME_ZONE, result_times_local=True)
         
        events = sm.get_solar_events(
            TEST_DATE, name_filter=sm.TWILIGHT_EVENT_NAMES)
         
        for event in events:
            actual = sm.get_solar_position(event.time).altitude
            expected = expected_altitudes[event.name[:3]]
            self.assertAlmostEqual(actual, expected, places=3)
    
    
class SunMoonTests2(SunMoonTests):
     
    """Tests a `SunMoon` that yields local result times."""
    
    RESULT_TIMES_LOCAL = True


class SunMoonCacheTests(TestCase):
    
    
    def test_initializer(self):
        
        dms = SunMoonCache.DEFAULT_MAX_SIZE
        
        cases = [
            ([], {}, (False, dms)),
            ([True], {}, (True, dms)),
            ([], {'max_size': dms - 1}, (False, dms - 1)),
            ([True, dms - 1], {}, (True, dms - 1)),
        ]
        
        for args, kwargs, expected in cases:
            actual = SunMoonCache(*args, **kwargs)
            self._assert_cache(actual, *expected)
    
    
    def _assert_cache(self, cache, result_times_local, max_size):
        self.assertEqual(cache.result_times_local, result_times_local)
        self.assertEqual(cache.max_size, max_size)
    
    
    def test_caching(self):
        
        lat_1 = 1
        lon_1 = 2
        tz_name_1 = 'US/Eastern'
        tz_1 = pytz.timezone(tz_name_1)
        
        lat_2 = 3
        lon_2 = 4
        tz_name_2 = 'US/Mountain'
        tz_2 = pytz.timezone(tz_name_2)
        
        for result_times_local in (False, True):
            
            cache = SunMoonCache(result_times_local)
            
            sm_1a = cache.get_sun_moon(lat_1, lon_1, tz_name_1)
            sm_1b = cache.get_sun_moon(lat_1, lon_1, tz_name_1)
            sm_1c = cache.get_sun_moon(lat_1, lon_1, tz_1)
            sm_2 = cache.get_sun_moon(lat_2, lon_2, tz_name_2)
            
            # Check that only one `SunMoon` is cached for the three
            # different versions of location 1.
            self.assertIs(sm_1b, sm_1a)
            self.assertIs(sm_1c, sm_1a)
            
            # Check that different `SunMoon` objects are stored for
            # locations 1 and 2.
            self.assertIsNot(sm_1a, sm_2)
            
            # Check `SunMoon` property values.
            self._assert_sun_moon(
                sm_1a, lat_1, lon_1, tz_1, result_times_local)
            self._assert_sun_moon(
                sm_2, lat_2, lon_2, tz_2, result_times_local)
    
    
    def _assert_sun_moon(
            self, sun_moon, latitude, longitude, time_zone,
            result_times_local):
        
        self.assertEqual(sun_moon.latitude, latitude)
        self.assertEqual(sun_moon.longitude, longitude)
        self.assertEqual(sun_moon.time_zone, time_zone)
        self.assertEqual(sun_moon.result_times_local, result_times_local)
