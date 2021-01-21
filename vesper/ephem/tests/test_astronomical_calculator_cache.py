import pytz

from vesper.ephem.astronomical_calculator import \
    AstronomicalCalculatorCache
from vesper.tests.test_case import TestCase


class AstronomicalCalculatorCacheTests(TestCase):
    
    
    def test_initializer(self):
        
        dms = AstronomicalCalculatorCache.DEFAULT_MAX_SIZE
        
        cases = [
            ([], {}, (False, dms)),
            ([True], {}, (True, dms)),
            ([], {'max_size': dms - 1}, (False, dms - 1)),
            ([True, dms - 1], {}, (True, dms - 1)),
        ]
        
        for args, kwargs, expected in cases:
            actual = AstronomicalCalculatorCache(*args, **kwargs)
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
            
            cache = AstronomicalCalculatorCache(result_times_local)
            
            calc_1a = cache.get_calculator(lat_1, lon_1, tz_name_1)
            calc_1b = cache.get_calculator(lat_1, lon_1, tz_name_1)
            calc_1c = cache.get_calculator(lat_1, lon_1, tz_1)
            calc_2 = cache.get_calculator(lat_2, lon_2, tz_name_2)
            
            # Check that only one calculator is cached for the three
            # different versions of location 1.
            self.assertIs(calc_1b, calc_1a)
            self.assertIs(calc_1c, calc_1a)
            
            # Check that different calculators are stored for locations
            # 1 and 2.
            self.assertIsNot(calc_1a, calc_2)
            
            # Check calculator property values.
            self._assert_calculator(
                calc_1a, lat_1, lon_1, tz_1, result_times_local)
            self._assert_calculator(
                calc_2, lat_2, lon_2, tz_2, result_times_local)
    
    
    def _assert_calculator(
            self, calculator, latitude, longitude, time_zone,
            result_times_local):
        
        self.assertEqual(calculator.latitude, latitude)
        self.assertEqual(calculator.longitude, longitude)
        self.assertEqual(calculator.time_zone, time_zone)
        self.assertEqual(calculator.result_times_local, result_times_local)
