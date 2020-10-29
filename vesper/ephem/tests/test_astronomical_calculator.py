import datetime

import pytz

from vesper.tests.test_case import TestCase
from vesper.ephem.astronomical_calculator import AstronomicalCalculator


# TODO: What effect does nonzero elevation have on calculated times?
# If none, maybe we should omit it?


ITHACA_LATITUDE = 42.431964
ITHACA_LONGITUDE = -76.501656


LUNAR_RISE_SET_DATA = [
    ((2020, 10, 19), (10, 48, 43), (20, 28, 21))
]

LUNAR_POSITION_DATA = [
    ((2020, 10, 19, 15), (25.37, 169.54, 364144))
]

SOLAR_POSITION_DATA = [
    ((2020, 10, 19, 15), (29.54, 217.15, 148972660))
]

ERROR_THRESHOLD = .002


class AstronomicalCalculatorTests(TestCase):


    def setUp(self):
        self.ithaca = AstronomicalCalculator(
            ITHACA_LATITUDE, ITHACA_LONGITUDE)
        
        
    def test_initializer(self):
        
        ithaca = self.ithaca
        self.assertEqual(ithaca.latitude, ITHACA_LATITUDE)
        self.assertEqual(ithaca.longitude, ITHACA_LONGITUDE)
        self.assertEqual(ithaca.elevation, 0)
        
        
    def test_get_solar_position(self):
        for datetime_args, expected_pos in LUNAR_POSITION_DATA:
            dt = _get_localized_datetime('US/Eastern', *datetime_args)
            pos = self.ithaca.get_solar_position(dt)
            self._check_pos(pos, expected_pos)
            
            
    def _check_pos(self, pos, expected_pos):
        
        alt, az, d = pos
        alt = alt.degrees
        az = az.degrees
        d = d.km
        
        x_alt, x_az, x_d = expected_pos
        
        self._check_relative_error(alt, x_alt, 'altitude')
        self._check_relative_error(az, x_az, 'azimuth')
        self._check_relative_error(d, x_d, 'distance')
               
        
    def _check_relative_error(self, a, b, name):
        error = abs((a - b) / b)
        print(f'{name} {a} {b} {error}')
        # self.assertLess(error, ERROR_THRESHOLD)
        
        
    def test_get_solar_events(self):
        d = datetime.date.today()
        start_dt = \
            _get_localized_datetime('US/Eastern', d.year, d.month, d.day)
        end_dt = start_dt + datetime.timedelta(days=1)
        events = self.ithaca.get_solar_events(start_dt, end_dt)
        self._show_solar_events(events, 'test_get_solar_events')
        
        
    def _show_solar_events(self, events, heading):
        print(heading + ':')
        for dt, name in events:
            print(dt, name)
        
        
    def test_get_day_solar_events(self):
        date = datetime.date.today()
        time_zone = pytz.timezone('US/Eastern')
        events = self.ithaca.get_day_solar_events(date, time_zone)
        self._show_solar_events(events, 'test_get_day_solar_events')
        
        
    def test_get_night_solar_events(self):
        date = datetime.date.today()
        time_zone = pytz.timezone('US/Eastern')
        events = self.ithaca.get_night_solar_events(date, time_zone)
        self._show_solar_events(events, 'test_get_night_solar_events')
        
        
    def test_get_lunar_position(self):
        for datetime_args, expected_pos in LUNAR_POSITION_DATA:
            dt = _get_localized_datetime('US/Eastern', *datetime_args)
            pos = self.ithaca.get_lunar_position(dt)
            self._check_pos(pos, expected_pos)
            
            
def _get_localized_datetime(time_zone_name, *datetime_args):
    time_zone = pytz.timezone(time_zone_name)
    naive_dt = datetime.datetime(*datetime_args)
    localized_dt = time_zone.localize(naive_dt)
    return localized_dt
