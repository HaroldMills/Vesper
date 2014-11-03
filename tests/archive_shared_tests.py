import datetime
import unittest

import pytz

import nfc.archive.archive_shared as archive_shared


class ArchiveSharedTests(unittest.TestCase):
    
    def test_get_night(self):
        
        dt = datetime.datetime
        d = datetime.date
        tz = pytz.timezone('US/Eastern')
        
        cases = [
            (dt(2012, 1, 1), d(2011, 12, 31)),
            (dt(2012, 1, 1, 11, 59, 59), d(2011, 12, 31)),
            (dt(2012, 1, 1, 12), d(2012, 1, 1)),
            (tz.localize(dt(2012, 1, 1)), d(2011, 12, 31))
        ]
        
        get_night = archive_shared.get_night
        
        for time, date in cases:
            self.assertEqual(get_night(time), date)
