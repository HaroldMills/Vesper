"""
Astronomical calculator unit tests.

Note that the related `test_skyfield` script uses the
`AstronomicalCalculator` class to test the `skyfield` package against
USNO data much more extensively than this module. That script takes
much longer to run than the tests of this module, however.
"""


import datetime

import pytz

from vesper.tests.test_case import TestCase
from vesper.ephem.astronomical_calculator import AstronomicalCalculator


# TODO: When the USNO web site is up again (as of 2020-12 it has been
# down for months, since it is "undergoing modernization efforts"), get
# more (and perhaps more accurate) solar and lunar position and
# illumination test data from it.

# TODO: Should we be using the USNO's NOVAS software for anything,
# for example for generating test data? There is a pip-installable
# Python wrapper for NOVAS available from PyPI.

# TODO: Test vector arguments to `get_solar_position`,
# `get_sunlight_period_name`, `get_lunar_position`, and
# `get_lunar_illumination`.


# Ithaca, NY location and time zone.
TEST_LAT = 42.431964
TEST_LON = -76.501656
TEST_ELEVATION = 0
TEST_TIME_ZONE_NAME = 'US/Eastern'
TEST_TIME_ZONE = pytz.timezone(TEST_TIME_ZONE_NAME)
TEST_DATE = datetime.date(2020, 10, 1)


def _time(*args):
    local_time = _get_localized_time(*args)
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time


def _get_localized_time(*args):
    naive_time = datetime.datetime(*args)
    return TEST_TIME_ZONE.localize(naive_time)


_date = datetime.date


def _round_time_to_nearest_minute(t):
    floor = t.replace(second=0, microsecond=0)
    delta = t - floor
    if delta.total_seconds() < 30:
        return floor
    else:
        return floor + datetime.timedelta(seconds=60)


SOLAR_POSITIONS = [
    (_time(2020, 1, 1, 0), (-70.51, 353.67, 147103121)),
    (_time(2021, 2, 1, 2), (-56.78, 47.77, 147410473)),
    (_time(2022, 3, 1, 4), (-30.28, 70.88, 148224283)),
    (_time(2023, 4, 1, 6), (-9.75, 74.69, 149473176)),
    (_time(2024, 5, 1, 8), (20.73, 87.87, 150747972)),
    (_time(2025, 6, 1, 10), (46.85, 103.21, 151703723)),
    (_time(2026, 7, 1, 12), (65.80, 137.62, 152090988)),
    (_time(2027, 8, 1, 14), (63.49, 206.09, 151837501)),
    (_time(2028, 9, 1, 16), (38.48, 240.68, 150948366)),
    (_time(2029, 10, 1, 18), (7.83, 257.93, 149749701)),
    (_time(2030, 11, 1, 20), (-22.82, 270.65, 148464087)),
    (_time(2031, 12, 1, 22), (-58.42, 301.27, 147509001)),
]
"""Solar position test data, obtained from suncalc.org on 2020-11-02."""


SOLAR_NOONS = [
    (_date(2020, 1, 1), _time(2020, 1, 1, 12, 9)),
    (_date(2021, 2, 1), _time(2021, 2, 1, 12, 19)),
    (_date(2022, 3, 1), _time(2022, 3, 1, 12, 18)),
    (_date(2023, 4, 1), _time(2023, 4, 1, 13, 9)),
    (_date(2024, 5, 1), _time(2024, 5, 1, 13, 3)),
    (_date(2025, 6, 1), _time(2025, 6, 1, 13, 3)),
    (_date(2026, 7, 1), _time(2026, 7, 1, 13, 9)),
    (_date(2027, 8, 1), _time(2027, 8, 1, 13, 12)),
    (_date(2028, 9, 1), _time(2028, 9, 1, 13, 5)),
    (_date(2029, 10, 1), _time(2029, 10, 1, 12, 55)),
    (_date(2030, 11, 1), _time(2030, 11, 1, 12, 49)),
    (_date(2031, 12, 1), _time(2031, 12, 1, 11, 55)),
]
"""Solar noon test data, obtained from timeanddate.com on 2021-01-04."""


SOLAR_MIDNIGHTS = [
    (_date(2020, 1, 1), _time(2020, 1, 2, 0, 9)),
    (_date(2021, 2, 1), _time(2021, 2, 2, 0, 19)),
    (_date(2022, 3, 1), _time(2022, 3, 2, 0, 18)),
    (_date(2023, 4, 1), _time(2023, 4, 2, 1, 9)),
    (_date(2024, 5, 1), _time(2024, 5, 2, 1, 2)),
    (_date(2025, 6, 1), _time(2025, 6, 2, 1, 4)),
    (_date(2026, 7, 1), _time(2026, 7, 2, 1, 10)),
    (_date(2027, 8, 1), _time(2027, 8, 2, 1, 12)),
    (_date(2028, 9, 1), _time(2028, 9, 2, 1, 5)),
    (_date(2029, 10, 1), _time(2029, 10, 2, 0, 55)),
    (_date(2030, 11, 1), _time(2030, 11, 2, 0, 49)),
    (_date(2031, 12, 1), _time(2031, 12, 1, 23, 55)),
]
"""Solar midnight test data, obtained from timeanddate.com on 2021-01-04."""


DAY_TWILIGHT_EVENTS = [
    (_time(2020, 10, 1, 5, 30), 'Astronomical Dawn'),
    (_time(2020, 10, 1, 6, 3), 'Nautical Dawn'),
    (_time(2020, 10, 1, 6, 36), 'Civil Dawn'),
    (_time(2020, 10, 1, 7, 4), 'Sunrise'),
    (_time(2020, 10, 1, 18, 47), 'Sunset'),
    (_time(2020, 10, 1, 19, 15), 'Civil Dusk'),
    (_time(2020, 10, 1, 19, 47), 'Nautical Dusk'),
    (_time(2020, 10, 1, 20, 20), 'Astronomical Dusk'),
]
"""Twilight event data for one day, obtained from USNO tables."""

NIGHT_TWILIGHT_EVENTS = [
    (_time(2020, 10, 1, 18, 47), 'Sunset'),
    (_time(2020, 10, 1, 19, 15), 'Civil Dusk'),
    (_time(2020, 10, 1, 19, 47), 'Nautical Dusk'),
    (_time(2020, 10, 1, 20, 20), 'Astronomical Dusk'),
    (_time(2020, 10, 2, 5, 31), 'Astronomical Dawn'),
    (_time(2020, 10, 2, 6, 4), 'Nautical Dawn'),
    (_time(2020, 10, 2, 6, 37), 'Civil Dawn'),
    (_time(2020, 10, 2, 7, 5), 'Sunrise'),
]
"""Twilight event data for one night, obtained from USNO tables."""

SUNLIGHT_PERIODS = [
    (_time(2020, 10, 1, 5, 25), 'Night'),
    (_time(2020, 10, 1, 5, 35), 'Morning Astronomical Twilight'),
    (_time(2020, 10, 1, 5, 58), 'Morning Astronomical Twilight'),
    (_time(2020, 10, 1, 6, 8), 'Morning Nautical Twilight'),
    (_time(2020, 10, 1, 6, 31), 'Morning Nautical Twilight'),
    (_time(2020, 10, 1, 6, 41), 'Morning Civil Twilight'),
    (_time(2020, 10, 1, 6, 59), 'Morning Civil Twilight'),
    (_time(2020, 10, 1, 7, 9), 'Day'),
    (_time(2020, 10, 1, 18, 42), 'Day'),
    (_time(2020, 10, 1, 18, 52), 'Evening Civil Twilight'),
    (_time(2020, 10, 1, 19, 10), 'Evening Civil Twilight'),
    (_time(2020, 10, 1, 19, 20), 'Evening Nautical Twilight'),
    (_time(2020, 10, 1, 19, 42), 'Evening Nautical Twilight'),
    (_time(2020, 10, 1, 19, 52), 'Evening Astronomical Twilight'),
    (_time(2020, 10, 1, 20, 15), 'Evening Astronomical Twilight'),
    (_time(2020, 10, 1, 20, 25), 'Night'),
]
"""Sunlight period data, derived from the event data above."""

LUNAR_DATA = [
    (_time(2020, 1, 1, 15, 46), (36.45, 151.09, 404551, .377)),
    (_time(2021, 2, 1, 15, 46), (-45.98, .41, 371142, .806)),
    (_time(2022, 3, 1, 15, 46), (8.22, 238.10, 372082, .012)),
    (_time(2023, 4, 1, 15, 46), (7.09, 71.76, 403880, .825)),
    (_time(2024, 5, 1, 15, 46), (-36.17, 274.30, 372332, .462)),
    (_time(2025, 6, 1, 15, 46), (46.36, 117.75, 388663, .368)),
    (_time(2026, 7, 1, 15, 46), (-66.08, 40.92, 402120, .969)),
    (_time(2027, 8, 1, 15, 46), (44.69, 256.23, 357556, .006)),
    (_time(2028, 9, 1, 15, 46), (-29.70, 82.53, 403409, .958)),
    (_time(2029, 10, 1, 15, 46), (-7.22, 304.71, 387778, .405)),
    (_time(2030, 11, 1, 15, 46), (19.73, 137.72, 372843, .426)),
    (_time(2031, 12, 1, 15, 46), (-26.11, 24.15, 403198, .921)),
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
SOLAR_ALT_AZ_ERROR_THRESHOLD = .12
SOLAR_DISTANCE_ERROR_THRESHOLD = .00012
LUNAR_ALT_AZ_ERROR_THRESHOLD = .14
LUNAR_DISTANCE_ERROR_THRESHOLD = .015
LUNAR_ILLUMINATION_ERROR_THRESHOLD = .070

TIME_DIFFERENCE_ERROR_THRESHOLD = 60   # seconds


class AstronomicalCalculatorTests(TestCase):
    
    """
    Tests an `AstronomicalCalculator` that yields UTC result times.
    """
    
    
    RESULT_TIMES_LOCAL = False
    
    
    def setUp(self):
        self.calculator = AstronomicalCalculator(
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
            actual = AstronomicalCalculator(*args, **kwargs)
            self._assert_calculator(actual, *expected)
    
    
    def _assert_calculator(
            self, calculator, latitude, longitude, time_zone,
            result_times_local):
        
        self.assertEqual(calculator.latitude, latitude)
        self.assertEqual(calculator.longitude, longitude)
        self.assertEqual(calculator.time_zone, time_zone)
        self.assertEqual(calculator.result_times_local, result_times_local)
    
    
    def test_get_solar_position(self):
        for time, expected_pos in SOLAR_POSITIONS:
            pos = self.calculator.get_solar_position(time)
            self._check_pos(
                pos, expected_pos, SOLAR_ALT_AZ_ERROR_THRESHOLD,
                SOLAR_DISTANCE_ERROR_THRESHOLD)
    
    
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
    
    
    def test_get_solar_noon(self):
        self._test_get_solar_noon_or_midnight(
            SOLAR_NOONS, self.calculator.get_solar_noon)
    
    
    def _test_get_solar_noon_or_midnight(self, cases, method):
        for date, expected in cases:
            actual = _round_time_to_nearest_minute(method(date))
            print(f'{str(actual)} {str(expected)}')
            self._assert_datetimes_nearly_equal(actual, expected)
    
    
    def test_get_solar_midnight(self):
        self._test_get_solar_noon_or_midnight(
            SOLAR_MIDNIGHTS, self.calculator.get_solar_midnight)
    
    
    def test_get_twilight_events(self):
        d = TEST_DATE
        start_time = _get_localized_time(d.year, d.month, d.day)
        end_time = start_time + datetime.timedelta(days=1)
        events = self.calculator.get_twilight_events(start_time, end_time)
        self._check_events(events, DAY_TWILIGHT_EVENTS)
    
    
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
        delta = (a - b).total_seconds()
        self.assertLessEqual(delta, TIME_DIFFERENCE_ERROR_THRESHOLD)
    
    
    def _show_twilight_events(self, events, heading):
        print(heading + ':')
        for time, name in events:
            print(time, name)
    
    
    def test_get_day_twilight_events(self):
        events = self.calculator.get_day_twilight_events(TEST_DATE)
        self._check_events(events, DAY_TWILIGHT_EVENTS)
    
    
    def test_get_night_twilight_events(self):
        events = self.calculator.get_night_twilight_events(TEST_DATE)
        self._check_events(events, NIGHT_TWILIGHT_EVENTS)
    
    
    def test_get_day_twilight_event_time(self):
        method = self.calculator.get_day_twilight_event_time
        self._test_get_date_twilight_event_time(method, DAY_TWILIGHT_EVENTS)
    
    
    def _test_get_date_twilight_event_time(self, method, events):
        for expected_time, event_name in events:
            actual_time = method(TEST_DATE, event_name)
            self._assert_datetimes_nearly_equal(actual_time, expected_time)
    
    
    def test_get_night_twilight_event_time(self):
        method = self.calculator.get_night_twilight_event_time
        self._test_get_date_twilight_event_time(method, NIGHT_TWILIGHT_EVENTS)
    
    
    def test_get_sunlight_period_name(self):
        for time, expected in SUNLIGHT_PERIODS:
            actual = self.calculator.get_sunlight_period_name(time)
            self.assertEqual(actual, expected)
    
    
    def test_get_lunar_position(self):
        for time, expected_pos in LUNAR_POSITIONS:
            pos = self.calculator.get_lunar_position(time)
            self._check_pos(
                pos, expected_pos, LUNAR_ALT_AZ_ERROR_THRESHOLD,
                LUNAR_DISTANCE_ERROR_THRESHOLD)
    
    
    def test_get_lunar_illumination(self):
        for time, expected_illumination in LUNAR_ILLUMINATIONS:
            illumination = self.calculator.get_lunar_illumination(time)
            self._check_relative_error(
                illumination, expected_illumination,
                LUNAR_ILLUMINATION_ERROR_THRESHOLD)
    
    
    def test_naive_datetime_errors(self):
         
        c = self.calculator
         
        # Methods that accept a single `datetime` argument.
        time = datetime.datetime(2020, 10, 1)
        self._assert_raises(ValueError, c.get_solar_position, time)
        self._assert_raises(ValueError, c.get_sunlight_period_name, time)
        self._assert_raises(ValueError, c.get_lunar_position, time)
        self._assert_raises(ValueError, c.get_lunar_illumination, time)
         
        # `get_twilight_events` with first `datetime` naive.
        time1 = datetime.datetime(2020, 10, 1)
        time2 = _get_localized_time(2020, 10, 2)
        self._assert_raises(ValueError, c.get_twilight_events, time1, time2)
         
        # `get_twilight_events` with second `datetime` naive.
        time1 = _get_localized_time(2020, 10, 1)
        time2 = datetime.datetime(2020, 10, 2)
        self._assert_raises(ValueError, c.get_twilight_events, time1, time2)
    
    
    def test_that_some_polar_functions_do_not_raise_exceptions(self):
        
        polar_latitudes = [-90, 90]
        time_1 = _get_localized_time(2020, 1, 1)
        time_2 = _get_localized_time(2021, 1, 1)
        
        for latitude in polar_latitudes:
            
            c = AstronomicalCalculator(latitude, TEST_LON, TEST_TIME_ZONE_NAME)
            
            cases = (
                (c.get_solar_position, time_1),
                (c.get_twilight_events, time_1, time_2),
                (c.get_lunar_position, time_1),
                (c.get_lunar_illumination, time_1)
            )
            
            for case in cases:
                method = case[0]
                args = case[1:]
                method(*args)
    
    
    def test_polar_errors(self):
        
        polar_latitudes = [-90, 90]
        date = datetime.date(2020, 1, 1)
        time = _get_localized_time(2020, 1, 1)
        
        for latitude in polar_latitudes:
            
            c = AstronomicalCalculator(latitude, TEST_LON, TEST_TIME_ZONE_NAME)
            
            cases = (
                (c.get_solar_noon, date),
                (c.get_solar_midnight, date),
                (c.get_day_twilight_events, date),
                (c.get_night_twilight_events, date),
                (c.get_day_twilight_event_time, date, 'Sunrise'),
                (c.get_night_twilight_event_time, date, 'Sunrise'),
                (c.get_sunlight_period_name, time),
            )
        
            for case in cases:
                self._assert_raises(ValueError, *case)
    
    
class AstronomicalCalculatorTests2(AstronomicalCalculatorTests):
     
    """
    Tests an `AstronomicalCalculator` that yields local result times.
    """
    
    
    RESULT_TIMES_LOCAL = True
