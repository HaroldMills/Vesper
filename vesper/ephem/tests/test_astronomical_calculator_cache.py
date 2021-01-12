import pytz

from vesper.ephem.astronomical_calculator import (
    AstronomicalCalculatorCache, Location)
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
        time_zone_1_name = 'US/Eastern'
        time_zone_1 = pytz.timezone(time_zone_1_name)
        
        lat_2 = 3
        lon_2 = 4
        time_zone_2_name = 'US/Mountain'
        
        loc_1a = Location(lat_1, lon_1, time_zone_1_name)
        loc_1b = Location(lat_1, lon_1, time_zone_1_name)
        loc_1c = Location(lat_1, lon_1, time_zone_1)
        loc_2 = Location(lat_2, lon_2, time_zone_2_name)
        
        for result_times_local in (False, True):
            
            cache = AstronomicalCalculatorCache(result_times_local)
            
            calc_1a = cache.get_calculator(loc_1a)
            calc_1b = cache.get_calculator(loc_1b)
            calc_1c = cache.get_calculator(loc_1c)
            calc_2 = cache.get_calculator(loc_2)
            
            # Check that only one calculator is cached for the three
            # different versions of location 1.
            self.assertIs(calc_1b, calc_1a)
            self.assertIs(calc_1c, calc_1a)
            
            # Check that different calculators are stored for locations
            # 1 and 2.
            self.assertIsNot(calc_1a, calc_2)
            
            # Check calculator property values.
            self._assert_calculator(calc_1a, loc_1a, result_times_local)
            self._assert_calculator(calc_2, loc_2, result_times_local)
    
    
    def _assert_calculator(self, calculator, location, result_times_local):
        self.assertEqual(calculator.location, location)
        self.assertEqual(calculator.result_times_local, result_times_local)
