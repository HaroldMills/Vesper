import pytz

from vesper.ephem.astronomical_calculator import Location
from vesper.tests.test_case import TestCase


class LocationTests(TestCase):
    
    
    def test_initializer(self):
        
        eastern_time_zone = pytz.timezone('US/Eastern')
        
        cases = [
            (1, 2, 'US/Eastern'),
            (1.5, 2.5, eastern_time_zone, 'Bobo'),
        ]
        
        for case in cases:
            loc = Location(*case)
            self.assertEqual(loc.latitude, case[0])
            self.assertEqual(loc.longitude, case[1])
            self.assertEqual(loc.time_zone, eastern_time_zone)
            if len(case) == 3:
                self.assertIsNone(loc.name)
            else:
                self.assertEqual(loc.name, case[3])
    
    
    def test_eq(self):
        
        a = Location(0, 0, 'US/Eastern')
        b = Location(0, 0, pytz.timezone('US/Eastern'))
        c = Location(1, 2, 'US/Central')
        
        self.assertNotEqual(a, 0)
        self.assertEqual(a, a)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)
    
    
    def test_hash(self):
        
        a = Location(0, 0, 'US/Eastern')
        b = Location(0, 0, pytz.timezone('US/Eastern'))
        c = Location(1, 2, 'US/Central')
        
        d = {}
        d[a] = 1
        d[b] = 2
        d[c] = 3
        
        self.assertEqual(len(d), 2)
        self.assertEqual(d[a], 2)
        self.assertEqual(d[b], 2)
        self.assertEqual(d[c], 3)
