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
# fraction illuminated test data from it.

# TODO: Should we be using the USNO's NOVAS software for anything,
# for example for generating test data? There is a pip-installable
# Python wrapper for NOVAS available from PyPI.

# TODO: Test vector arguments to `get_solar_position`,
# `get_solar_altitude_period_name`, `get_lunar_position`, and
# `get_lunar_fraction_illuminated`.


# Ithaca, NY location and time zone.
TEST_LAT = 42.431964
TEST_LON = -76.501656
TEST_ELEVATION = 0
TEST_TIME_ZONE_NAME = 'US/Eastern'
TEST_TIME_ZONE = pytz.timezone(TEST_TIME_ZONE_NAME)
TEST_DATE = datetime.date(2020, 10, 1)


def _dt(*args):
    local_dt = _get_localized_datetime(*args)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt


def _get_localized_datetime(*args):
    naive_dt = datetime.datetime(*args)
    return TEST_TIME_ZONE.localize(naive_dt)


SOLAR_POSITIONS = [
    (_dt(2020, 1, 1, 0), (-70.51, 353.67, 147103121)),
    (_dt(2021, 2, 1, 2), (-56.78, 47.77, 147410473)),
    (_dt(2022, 3, 1, 4), (-30.28, 70.88, 148224283)),
    (_dt(2023, 4, 1, 6), (-9.75, 74.69, 149473176)),
    (_dt(2024, 5, 1, 8), (20.73, 87.87, 150747972)),
    (_dt(2025, 6, 1, 10), (46.85, 103.21, 151703723)),
    (_dt(2026, 7, 1, 12), (65.80, 137.62, 152090988)),
    (_dt(2027, 8, 1, 14), (63.49, 206.09, 151837501)),
    (_dt(2028, 9, 1, 16), (38.48, 240.68, 150948366)),
    (_dt(2029, 10, 1, 18), (7.83, 257.93, 149749701)),
    (_dt(2030, 11, 1, 20), (-22.82, 270.65, 148464087)),
    (_dt(2031, 12, 1, 22), (-58.42, 301.27, 147509001)),
]
"""Solar position test data, obtained from suncalc.org on 2020-11-02."""

DAY_SOLAR_ALTITUDE_EVENTS = [
    (_dt(2020, 10, 1, 5, 30), 'Astronomical Dawn'),
    (_dt(2020, 10, 1, 6, 3), 'Nautical Dawn'),
    (_dt(2020, 10, 1, 6, 36), 'Civil Dawn'),
    (_dt(2020, 10, 1, 7, 4), 'Sunrise'),
    (_dt(2020, 10, 1, 18, 47), 'Sunset'),
    (_dt(2020, 10, 1, 19, 15), 'Civil Dusk'),
    (_dt(2020, 10, 1, 19, 47), 'Nautical Dusk'),
    (_dt(2020, 10, 1, 20, 20), 'Astronomical Dusk'),
]
"""Solar altitude event data for one day, obtained from USNO tables."""

NIGHT_SOLAR_ALTITUDE_EVENTS = [
    (_dt(2020, 10, 1, 18, 47), 'Sunset'),
    (_dt(2020, 10, 1, 19, 15), 'Civil Dusk'),
    (_dt(2020, 10, 1, 19, 47), 'Nautical Dusk'),
    (_dt(2020, 10, 1, 20, 20), 'Astronomical Dusk'),
    (_dt(2020, 10, 2, 5, 31), 'Astronomical Dawn'),
    (_dt(2020, 10, 2, 6, 4), 'Nautical Dawn'),
    (_dt(2020, 10, 2, 6, 37), 'Civil Dawn'),
    (_dt(2020, 10, 2, 7, 5), 'Sunrise'),
]
"""Solar altitude event data for one night, obtained from USNO tables."""

SOLAR_ALTITUDE_PERIODS = [
    (_dt(2020, 10, 1, 5, 25), 'Night'),
    (_dt(2020, 10, 1, 5, 35), 'Astronomical Twilight'),
    (_dt(2020, 10, 1, 5, 58), 'Astronomical Twilight'),
    (_dt(2020, 10, 1, 6, 8), 'Nautical Twilight'),
    (_dt(2020, 10, 1, 6, 31), 'Nautical Twilight'),
    (_dt(2020, 10, 1, 6, 41), 'Civil Twilight'),
    (_dt(2020, 10, 1, 6, 59), 'Civil Twilight'),
    (_dt(2020, 10, 1, 7, 9), 'Day'),
    (_dt(2020, 10, 1, 18, 42), 'Day'),
    (_dt(2020, 10, 1, 18, 52), 'Civil Twilight'),
    (_dt(2020, 10, 1, 19, 10), 'Civil Twilight'),
    (_dt(2020, 10, 1, 19, 20), 'Nautical Twilight'),
    (_dt(2020, 10, 1, 19, 42), 'Nautical Twilight'),
    (_dt(2020, 10, 1, 19, 52), 'Astronomical Twilight'),
    (_dt(2020, 10, 1, 20, 15), 'Astronomical Twilight'),
    (_dt(2020, 10, 1, 20, 25), 'Night'),
]
"""Solar altitude period data, derived from the event data above."""

LUNAR_DATA = [
    (_dt(2020, 1, 1, 15, 46), (36.45, 151.09, 404551, .377)),
    (_dt(2021, 2, 1, 15, 46), (-45.98, .41, 371142, .806)),
    (_dt(2022, 3, 1, 15, 46), (8.22, 238.10, 372082, .012)),
    (_dt(2023, 4, 1, 15, 46), (7.09, 71.76, 403880, .825)),
    (_dt(2024, 5, 1, 15, 46), (-36.17, 274.30, 372332, .462)),
    (_dt(2025, 6, 1, 15, 46), (46.36, 117.75, 388663, .368)),
    (_dt(2026, 7, 1, 15, 46), (-66.08, 40.92, 402120, .969)),
    (_dt(2027, 8, 1, 15, 46), (44.69, 256.23, 357556, .006)),
    (_dt(2028, 9, 1, 15, 46), (-29.70, 82.53, 403409, .958)),
    (_dt(2029, 10, 1, 15, 46), (-7.22, 304.71, 387778, .405)),
    (_dt(2030, 11, 1, 15, 46), (19.73, 137.72, 372843, .426)),
    (_dt(2031, 12, 1, 15, 46), (-26.11, 24.15, 403198, .921)),
]
"""
Lunar position and fraction illuminated test data, obtained from
suncalc.org on 2020-11-02.
"""

LUNAR_POSITIONS = [(dt, d[:3]) for dt, d in LUNAR_DATA]

LUNAR_FRACTIONS_ILLUMINATED = [(dt, d[3]) for dt, d in LUNAR_DATA]

# The following were set to the minimum values with two significant digits
# that were required for tests involving suncalc.org and mooncalc.org test
# data to pass. Hopefully the larger thresholds can be reduced when the
# USNO web site is up again and we can obtain more and hopefully more
# accurate test data from it.
SOLAR_ALT_AZ_ERROR_THRESHOLD = .12
SOLAR_DISTANCE_ERROR_THRESHOLD = .00012
LUNAR_ALT_AZ_ERROR_THRESHOLD = .14
LUNAR_DISTANCE_ERROR_THRESHOLD = .015
LUNAR_FRACTION_ILLUMINATED_ERROR_THRESHOLD = .070

TIME_DIFFERENCE_ERROR_THRESHOLD = 60   # seconds


class AstronomicalCalculatorTests(TestCase):

    """Tests for `AstronomicalCalculator` with UTC result times."""
    
    
    def setUp(self):
        self.calculator = AstronomicalCalculator(
            TEST_LAT, TEST_LON, local_time_zone=TEST_TIME_ZONE_NAME)
        
        
    def test_initializer(self):
        
        cases = (
            
            ((), {}, (0, None, pytz.utc)),
            
            ((0,), {}, (0, None, pytz.utc)),
            
            ((0, TEST_TIME_ZONE_NAME), {}, (0, TEST_TIME_ZONE, pytz.utc)),
            
            ((0, TEST_TIME_ZONE), {}, (0, TEST_TIME_ZONE, pytz.utc)),
            
            ((0, TEST_TIME_ZONE_NAME, None), {},
                (0, TEST_TIME_ZONE, pytz.utc)),
            
            ((0, TEST_TIME_ZONE, TEST_TIME_ZONE_NAME), {}, 
                (0, TEST_TIME_ZONE, TEST_TIME_ZONE)),
            
            ((), {'local_time_zone': TEST_TIME_ZONE_NAME},
                (0, TEST_TIME_ZONE, pytz.utc)),
            
            ((), {'local_time_zone': TEST_TIME_ZONE},
                (0, TEST_TIME_ZONE, pytz.utc)),
            
            ((), {'result_time_zone': TEST_TIME_ZONE_NAME},
                (0, None, TEST_TIME_ZONE)),
            
            ((), {'result_time_zone': TEST_TIME_ZONE},
                (0, None, TEST_TIME_ZONE)),
            
            ((0, TEST_TIME_ZONE_NAME),
                {'result_time_zone': TEST_TIME_ZONE_NAME},
                (0, TEST_TIME_ZONE, TEST_TIME_ZONE)),
            
        )
        
        for args, kwargs, expected in cases:
            self._test_initializer(
                TEST_LAT, TEST_LON, args, kwargs, expected)
        
        
    def _test_initializer(self, lat, lon, args, kwargs, expected):
        elevation, local_time_zone, result_time_zone = expected
        c = AstronomicalCalculator(lat, lon, *args, **kwargs)
        self.assertEqual(c.latitude, TEST_LAT)
        self.assertEqual(c.longitude, TEST_LON)
        self.assertEqual(c.elevation, elevation)
        self.assertEqual(c.local_time_zone, local_time_zone)
        self.assertEqual(c.result_time_zone, result_time_zone)
        
        
    def test_get_solar_position(self):
        for dt, expected_pos in SOLAR_POSITIONS:
            pos = self.calculator.get_solar_position(dt)
            self._check_pos(
                pos, expected_pos, SOLAR_ALT_AZ_ERROR_THRESHOLD,
                SOLAR_DISTANCE_ERROR_THRESHOLD)
            
            
    def _check_pos(
            self, pos, expected_pos, alt_az_error_threshold,
            distance_error_threshold):
        
        alt, az, d = pos
        alt = alt.degrees
        az = az.degrees
        d = d.km
        
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
        
        
    def test_get_solar_altitude_events(self):
        d = TEST_DATE
        start_dt = _get_localized_datetime(d.year, d.month, d.day)
        end_dt = start_dt + datetime.timedelta(days=1)
        events = self.calculator.get_solar_altitude_events(start_dt, end_dt)
        self._check_events(events, DAY_SOLAR_ALTITUDE_EVENTS)
        
        
    def _check_events(self, actual_events, expected_events):
        
        self.assertEqual(len(actual_events), len(expected_events))
        
        for i, (actual_dt, actual_name) in enumerate(actual_events):
            expected_dt, expected_name = expected_events[i]
            self._assert_datetimes_nearly_equal(actual_dt, expected_dt)
            self._assert_result_time_zone(actual_dt)
            self.assertEqual(actual_name, expected_name)
        
        
    def _assert_datetimes_nearly_equal(self, a, b):
        delta = (a - b).total_seconds()
        self.assertLess(delta, TIME_DIFFERENCE_ERROR_THRESHOLD)
        
        
    def _assert_result_time_zone(self, dt):
        self.assertEqual(dt.tzinfo.zone, self.calculator.result_time_zone.zone)
        
        
    def _show_solar_altitude_events(self, events, heading):
        print(heading + ':')
        for dt, name in events:
            print(dt, name)
        
        
    def test_get_day_solar_altitude_events(self):
        events = self.calculator.get_day_solar_altitude_events(TEST_DATE)
        self._check_events(events, DAY_SOLAR_ALTITUDE_EVENTS)
        
        
    def test_get_day_solar_altitude_event_time(self):
        for expected_dt, event_name in DAY_SOLAR_ALTITUDE_EVENTS:
            actual_dt = self.calculator.get_day_solar_altitude_event_time(
                TEST_DATE, event_name)
            self._assert_datetimes_nearly_equal(actual_dt, expected_dt)
        
        
    def test_get_night_solar_altitude_events(self):
        events = self.calculator.get_night_solar_altitude_events(TEST_DATE)
        self._check_events(events, NIGHT_SOLAR_ALTITUDE_EVENTS)
        
        
    def test_get_night_solar_altitude_event_time(self):
        for expected_dt, event_name in NIGHT_SOLAR_ALTITUDE_EVENTS:
            actual_dt = self.calculator.get_night_solar_altitude_event_time(
                TEST_DATE, event_name)
            self._assert_datetimes_nearly_equal(actual_dt, expected_dt)
        
        
    def test_get_solar_altitude_period_name(self):
        for dt, expected in SOLAR_ALTITUDE_PERIODS:
            actual = self.calculator.get_solar_altitude_period_name(dt)
            self.assertEqual(actual, expected)
            
            
    def test_get_lunar_position(self):
        for dt, expected_pos in LUNAR_POSITIONS:
            pos = self.calculator.get_lunar_position(dt)
            self._check_pos(
                pos, expected_pos, LUNAR_ALT_AZ_ERROR_THRESHOLD,
                LUNAR_DISTANCE_ERROR_THRESHOLD)
             
            
    def test_get_lunar_fraction_illuminated(self):
        for dt, expected_fi in LUNAR_FRACTIONS_ILLUMINATED:
            fi = self.calculator.get_lunar_fraction_illuminated(dt)
            self._check_relative_error(
                fi, expected_fi, LUNAR_FRACTION_ILLUMINATED_ERROR_THRESHOLD)


class AstronomicalCalculatorTests2(AstronomicalCalculatorTests):
    
    """Tests for `AstronomicalCalculator` with US/Eastern result times."""


    def setUp(self):
        self.calculator = AstronomicalCalculator(
            TEST_LAT, TEST_LON, local_time_zone=TEST_TIME_ZONE_NAME,
            result_time_zone=TEST_TIME_ZONE_NAME)
