import datetime
import unittest

import pytz

import vesper.util.yaml_utils as yaml_utils


_DT = datetime.datetime


class PresetManagerTests(unittest.TestCase):
    
    
    def testDateTimeParsing(self):
        
        cases = (
                 
            ('2016-05-18 12:34:56', _DT(2016, 5, 18, 12, 34, 56)),
            
            ('2016-05-18', _DT(2016, 5, 18)),
            
            ('2016-05-18 12:34:56.789123',
                 _DT(2016, 5, 18, 12, 34, 56, 789123)),
                 
            ('2016-05-18 12:34:56.789123-04:00',
                 _DT(2016, 5, 18, 16, 34, 56, 789123, pytz.utc))
                 
        )
        
        for s, expected in cases:
            d = yaml_utils.load(s)
            self.assertEqual(d, expected)
