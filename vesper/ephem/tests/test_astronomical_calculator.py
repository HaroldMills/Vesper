import datetime

import pytz

from vesper.tests.test_case import TestCase
from vesper.ephem.astronomical_calculator import AstronomicalCalculator


# TODO: When the USNO web site is up again (as of 2020-11 it has been
# down for months, since it is "undergoing modernization efforts"), get
# more (and perhaps more accurate) solar and lunar position and
# fraction illuminated test data from it.


# Ithaca, NY location and time zone.
TEST_LATITUDE = 42.431964
TEST_LONGITUDE = -76.501656
TEST_TIME_ZONE = pytz.timezone('US/Eastern')

SOLAR_POSITIONS = [
    ((2020, 1, 1, 0), (-70.51, 353.67, 147103121)),
    ((2021, 2, 1, 2), (-56.78, 47.77, 147410473)),
    ((2022, 3, 1, 4), (-30.28, 70.88, 148224283)),
    ((2023, 4, 1, 6), (-9.75, 74.69, 149473176)),
    ((2024, 5, 1, 8), (20.73, 87.87, 150747972)),
    ((2025, 6, 1, 10), (46.85, 103.21, 151703723)),
    ((2026, 7, 1, 12), (65.80, 137.62, 152090988)),
    ((2027, 8, 1, 14), (63.49, 206.09, 151837501)),
    ((2028, 9, 1, 16), (38.48, 240.68, 150948366)),
    ((2029, 10, 1, 18), (7.83, 257.93, 149749701)),
    ((2030, 11, 1, 20), (-22.82, 270.65, 148464087)),
    ((2031, 12, 1, 22), (-58.42, 301.27, 147509001)),
]
"""
Solar position test data, obtained from suncalc.org on 2020-11-02.
"""

SOLAR_ALTITUDE_EVENTS_DATE = (2020, 10, 1)

SOLAR_ALTITUDE_EVENTS = [
    ('0530', 'Astronomical Dawn'),
    ('0603', 'Nautical Dawn'),
    ('0636', 'Civil Dawn'),
    ('0704', 'Sunrise'),
    ('1847', 'Sunset'),
    ('1915', 'Civil Dusk'),
    ('1947', 'Nautical Dusk'),
    ('2020', 'Astronomical Dusk')
]
"""
Solar altitude event data, obtained from USNO tables.

The `test_skyfield` script tests the `get_solar_altitude_events`
method much more thoroughly than we do in these unit tests. These
tests are only a quick sanity check.
"""

SOLAR_ALTITUDE_PERIODS = [
    ('0525', 'Night'),
    ('0535', 'Astronomical Twilight'),
    ('0558', 'Astronomical Twilight'),
    ('0608', 'Nautical Twilight'),
    ('0631', 'Nautical Twilight'),
    ('0641', 'Civil Twilight'),
    ('0659', 'Civil Twilight'),
    ('0709', 'Day'),
    ('1842', 'Day'),
    ('1852', 'Civil Twilight'),
    ('1910', 'Civil Twilight'),
    ('1920', 'Nautical Twilight'),
    ('1942', 'Nautical Twilight'),
    ('1952', 'Astronomical Twilight'),
    ('2015', 'Astronomical Twilight'),
    ('2025', 'Night'),
]
"""
Solar altitude period data, derived from the event data above.
"""

LUNAR_DATA = [
    ((2020, 1, 1, 15, 46), (36.45, 151.09, 404551, .377)),
    ((2021, 2, 1, 15, 46), (-45.98, .41, 371142, .806)),
    ((2022, 3, 1, 15, 46), (8.22, 238.10, 372082, .012)),
    ((2023, 4, 1, 15, 46), (7.09, 71.76, 403880, .825)),
    ((2024, 5, 1, 15, 46), (-36.17, 274.30, 372332, .462)),
    ((2025, 6, 1, 15, 46), (46.36, 117.75, 388663, .368)),
    ((2026, 7, 1, 15, 46), (-66.08, 40.92, 402120, .969)),
    ((2027, 8, 1, 15, 46), (44.69, 256.23, 357556, .006)),
    ((2028, 9, 1, 15, 46), (-29.70, 82.53, 403409, .958)),
    ((2029, 10, 1, 15, 46), (-7.22, 304.71, 387778, .405)),
    ((2030, 11, 1, 15, 46), (19.73, 137.72, 372843, .426)),
    ((2031, 12, 1, 15, 46), (-26.11, 24.15, 403198, .921)),
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


# TODO: Test vector arguments to `get_solar_position`,
# `get_solar_altitude_period`, `get_lunar_position`, and
# `get_lunar_fraction_illuminated`.


class AstronomicalCalculatorTests(TestCase):


    def setUp(self):
        self.calculator = AstronomicalCalculator(
            TEST_LATITUDE, TEST_LONGITUDE)
        
        
    def test_initializer(self):
        calculator = self.calculator
        self.assertEqual(calculator.latitude, TEST_LATITUDE)
        self.assertEqual(calculator.longitude, TEST_LONGITUDE)
        self.assertEqual(calculator.elevation, 0)
        
        
    def test_get_solar_position(self):
        for datetime_args, expected_pos in SOLAR_POSITIONS:
            dt = _get_localized_datetime(*datetime_args)
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
         
        start_dt = _get_localized_datetime(*SOLAR_ALTITUDE_EVENTS_DATE)
        end_dt = start_dt + datetime.timedelta(days=1)
        events = self.calculator.get_solar_altitude_events(start_dt, end_dt)
         
        expected_events = _parse_time_name_pairs(SOLAR_ALTITUDE_EVENTS)
         
        self.assertEqual(len(events), len(expected_events))
        
        for i, (actual_dt, actual_name) in enumerate(events):
            expected_dt, expected_name = expected_events[i]
            self._assert_datetimes_nearly_equal(actual_dt, expected_dt)
            self.assertEqual(actual_name, expected_name)
        
        
    def _assert_datetimes_nearly_equal(self, a, b):
        delta = (a - b).total_seconds()
        self.assertLess(delta, TIME_DIFFERENCE_ERROR_THRESHOLD)
        
        
    def _show_solar_altitude_events(self, events, heading):
        print(heading + ':')
        for dt, name in events:
            print(dt, name)
        
        
    def test_get_solar_altitude_period(self):
        cases = _parse_time_name_pairs(SOLAR_ALTITUDE_PERIODS)
        for dt, expected in cases:
            actual = self.calculator.get_solar_altitude_period(dt)
            self.assertEqual(actual, expected)
            
            
    def test_get_lunar_position(self):
        for datetime_args, expected_pos in LUNAR_POSITIONS:
            dt = _get_localized_datetime(*datetime_args)
            pos = self.calculator.get_lunar_position(dt)
            self._check_pos(
                pos, expected_pos, LUNAR_ALT_AZ_ERROR_THRESHOLD,
                LUNAR_DISTANCE_ERROR_THRESHOLD)
             
            
    def test_get_lunar_fraction_illuminated(self):
        for datetime_args, expected_fi in LUNAR_FRACTIONS_ILLUMINATED:
            dt = _get_localized_datetime(*datetime_args)
            fi = self.calculator.get_lunar_fraction_illuminated(dt)
            self._check_relative_error(
                fi, expected_fi, LUNAR_FRACTION_ILLUMINATED_ERROR_THRESHOLD)


def _get_localized_datetime(*args):
    naive_dt = datetime.datetime(*args)
    return TEST_TIME_ZONE.localize(naive_dt)


def _parse_time_name_pairs(pairs):
    return [(_parse_time(time), name) for time, name in pairs]


def _parse_time(hhmm):
    hour = int(hhmm[:2])
    minute = int(hhmm[2:])
    args = SOLAR_ALTITUDE_EVENTS_DATE + (hour, minute)
    local_dt = _get_localized_datetime(*args)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt
