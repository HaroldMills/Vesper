from __future__ import print_function
import datetime

from test_case import TestCase
from vesper.util.usno_altitude_azimuth_table import UsnoAltitudeAzimuthTable
import vesper.util.usno_utils as usno_utils


class UsnoAltitudeAzimuthTableTests(TestCase):


    # I have commented this out so we don't hit the USNO web site every
    # time we run Vesper unit tests.
#     def test_download_table_text(self):
#         text = UsnoAltitudeAzimuthTable.download_table_text(
#             'Sun Altitude/Azimuth', 42.45, -76.5,
#             datetime.date(2016, 2, 17), 119, -4, 'Ithaca, NY')
#         self.assertEqual(text.strip(), _ITHACA_SUN_TABLE.strip())
        
        
    def test_ithaca_sun_table(self):
        header = ('Sun',) + _ITHACA_HEADER_DATA
        data = (
            ('07:56', -1.6, 104.9),
            ('17:51', 7.8, 246.0)
        )
        self._test_table(_ITHACA_SUN_TABLE, header, 6, data)
         
         
    def _test_table(
            self, table, expected_header, expected_size, expected_data):
        
        table = UsnoAltitudeAzimuthTable(table)
        self._check_header(table, *expected_header)
        self._check_body(table, expected_size, expected_data)
         
         
    def _check_header(
            self, table, table_type, place_name, lat, lon, date, utc_offset):
        
        self.assertEqual(table.type, table_type)
        self.assertEqual(table.place_name, place_name)
        self.assertEqual(table.lat, lat)
        self.assertEqual(table.lon, lon)
        self.assertEqual(table.date, date)
        
        utc_offset = datetime.timedelta(hours=utc_offset)
        self.assertEqual(table.utc_offset, utc_offset)
        
        
    def _check_body(self, table, expected_size, expected_data):
        
        data = dict((d[0], d[1:]) for d in table.data)
        
        self.assertEqual(len(data), expected_size)
        
        for e_d in expected_data:
            time = usno_utils.parse_time(e_d[0], table.date, table.utc_offset)
            d = data.get(time)
            self.assertNotEqual(d, None)
            self.assertEqual(d, e_d[1:])
        
        
    def test_ithaca_moon_table(self):
        header = ('Moon',) + _ITHACA_HEADER_DATA
        data = (
            ('04:00', -.1, 294.5, .72),
            ('14:00', -1.6, 64.2, .76)
        )
        self._test_table(_ITHACA_MOON_TABLE, header, 8, data)
                
        
    def test_ithaca_sun_utc_table(self):
        header = ('Sun',) + _ITHACA_HEADER_DATA[:-1] + (0,)
        data = (
            ('12:00', -.9, 105.6),
            ('22:00', 6.3, 247.6)
        )
        self._test_table(_ITHACA_SUN_UTC_TABLE, header, 6, data)
         
         
    def test_zero_lat_lon_sun_table(self):
        header = ('Sun', '', 0, 0, datetime.date(2016, 2, 1), 0)
        data = (
            ('06:00', -3.2, 107.3),
            ('18:00', 3.4, 252.9)
        )
        self._test_table(_ZERO_LAT_LON_SUN_TABLE, header, 7, data)
         
         
    def test_high_latitude_sun_table(self):
        header = ('Sun', '', 85, -120, datetime.date(2016, 12, 20), 0)
        self._test_table(_HIGH_LATITUDE_SUN_TABLE, header, 0, ())
        
        
    def test_single_digit_lat_lon_sun_table(self):
        header = ('Sun', '', 5, -5, datetime.date(2016, 12, 20), 0)
        data = (
            ('06:00', -6, 113.1),
            ('18:00', 2.4, 246.3)
        )
        self._test_table(_SINGLE_DIGIT_LAT_LON_SUN_TABLE, header, 7, data)
         
         
    def test_east_south_sun_table(self):
        header = ('Sun', '', -42.45, 76.5, datetime.date(2016, 2, 17), 4)
        data = (
            ('04:00', -3.9, 110.5),
            ('18:00', -1.2, 252.4)
        )
        self._test_table(_EAST_SOUTH_SUN_TABLE, header, 8, data)
        
        
_ITHACA_HEADER_DATA = \
    ('ITHACA, NY', 42.45, -76.5, datetime.date(2016, 2, 17), -4)


# Note that this table has an interval of 119 minutes rather than the
# 120 minutes of all of the other tables. This ensures that the minutes
# digits of the times in the table are not all zero so that we can
# adequately test our time parsing code.
_ITHACA_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
ITHACA, NY                                                                    
   o  ,    o  ,                                                               
W 76 30, N42 27
                                                              
Altitude and Azimuth of the Sun                                               
Feb 17, 2016
                                                                 
Zone:  4h West of Greenwich
                                                  
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
07:56       -1.6       104.9
09:55       18.1       126.6
11:54       32.1       155.0
13:53       35.1       189.9
15:52       25.4       221.8
17:51        7.8       246.0
'''


_ITHACA_MOON_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
ITHACA, NY                                                                    
   o  ,    o  ,                                                               
W 76 30, N42 27
                                                              
Altitude and Azimuth of the Moon                                              
Feb 17, 2016
                                                                 
Zone:  4h West of Greenwich
                                                  
          Altitude    Azimuth    Fraction                                     
                      (E of N)  Illuminated
                                  
 h  m         o           o                                                   
                                                                              
                                                                              
00:00       41.1       255.0       0.70
02:00       19.9       275.8       0.71
04:00       -0.1       294.5       0.72

14:00       -1.6        64.2       0.76
16:00       18.9        82.9       0.76
18:00       40.2       103.4       0.77
20:00       59.1       135.9       0.78
22:00       64.7       196.2       0.79
'''


_ITHACA_SUN_UTC_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
ITHACA, NY                                                                    
   o  ,    o  ,                                                               
W 76 30, N42 27
                                                              
Altitude and Azimuth of the Sun                                               
Feb 17, 2016
                                                                 
Universal Time
                                                               
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
12:00       -0.9       105.6
14:00       18.9       127.7
16:00       32.5       156.6
18:00       34.8       191.9
20:00       24.4       223.7
22:00        6.3       247.6
'''


_ZERO_LAT_LON_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
                                                                              
   o  ,    o  ,                                                               
   0 00,   0 00
                                                              
Altitude and Azimuth of the Sun                                               
Feb 1, 2016
                                                                  
Universal Time
                                                               
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
06:00       -3.2       107.3
08:00       25.4       109.1
10:00       52.9       119.4
12:00       72.5       169.2
14:00       58.7       235.4
16:00       31.7       249.7
18:00        3.4       252.9
'''


_HIGH_LATITUDE_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
                                                                              
   o  ,    o  ,                                                               
W120 00, N85 00
                                                              
Altitude and Azimuth of the Sun                                               
Dec 20, 2016
                                                                 
Universal Time
                                                               
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
OBJECT IS CONTINUOUSLY BELOW THE HORIZON.
'''


_SINGLE_DIGIT_LAT_LON_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
                                                                              
   o  ,    o  ,                                                               
W  5 00, N 5 00
                                                              
Altitude and Azimuth of the Sun                                               
Dec 20, 2016
                                                                 
Universal Time
                                                               
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
06:00       -6.0       113.1
08:00       21.1       117.5
10:00       46.0       131.7
12:00       61.2       171.5
14:00       52.2       220.2
16:00       28.9       239.7
18:00        2.4       246.3
'''


_EAST_SOUTH_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
                                                                              
   o  ,    o  ,                                                               
E 76 30, S42 27
                                                              
Altitude and Azimuth of the Sun                                               
Feb 17, 2016
                                                                 
Zone:  4h East of Greenwich
                                                  
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
04:00       -3.9       110.5
06:00       17.8        90.5
08:00       39.4        67.7
10:00       56.3        31.0
12:00       57.7       335.7
14:00       42.0       296.2
16:00       20.7       272.4
18:00       -1.2       252.4
'''
