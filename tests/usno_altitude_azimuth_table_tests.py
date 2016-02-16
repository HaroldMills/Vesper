from __future__ import print_function
import datetime

from test_case import TestCase
from vesper.util.usno_altitude_azimuth_table import UsnoAltitudeAzimuthTable


class UsnoAltitudeAzimuthTableTests(TestCase):


    # I have commented this out so we don't hit the USNO web site every
    # time we run Vesper unit tests.
#     def test_download_table_text(self):
#         text = UsnoAltitudeAzimuthTable.download_table_text(
#             'Sun', 42.45, -76.5, datetime.date(2016, 2, 10), 10, -5,
#             'Ithaca, NY')
#         pass
        
        
    def test_ithaca_sun_table(self):
        header = ('Sun',) + _ITHACA_HEADER_DATA
        self._test_table(_ITHACA_SUN_TABLE, header)
        
        
    def _test_table(self, table, expected_header):
        table = UsnoAltitudeAzimuthTable(table)
        self._check_header(table, *expected_header)
        
        
    def test_ithaca_moon_table(self):
        header = ('Moon',) + _ITHACA_HEADER_DATA
        self._test_table(_ITHACA_MOON_TABLE, header)
                
        
    def _check_header(
            self, table, table_type, place_name, lat, lon, date, utc_offset):
        
        self.assertEqual(table.type, table_type)
        self.assertEqual(table.place_name, place_name)
        self.assertEqual(table.lat, lat)
        self.assertEqual(table.lon, lon)
        self.assertEqual(table.date, date)
        self.assertEqual(table.utc_offset, utc_offset)
        
        
_ITHACA_HEADER_DATA = \
    ('ITHACA, NY', 42.45, -76.5, datetime.date(2016, 2, 10), -5)


_ITHACA_SUN_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
ITHACA, NY                                                                   
   o  ,    o  ,                                                               
W 76 30, N42 27
                                                              
Altitude and Azimuth of the Sun                                               
Feb 10, 2016
                                                                 
Zone:  5h West of Greenwich
                                                  
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
06:10      -11.6        99.1
06:20       -9.7       100.7
06:30       -7.9       102.4
06:40       -6.1       104.0
06:50       -4.3       105.6
07:00       -2.6       107.3
07:10       -0.8       109.0
07:20        1.3       110.6
07:30        2.9       112.4
07:40        4.5       114.1
07:50        6.1       115.8
08:00        7.8       117.6
08:10        9.4       119.4
08:20       11.0       121.3
08:30       12.5       123.2
08:40       14.0       125.1
08:50       15.5       127.1
09:00       17.0       129.1
09:10       18.4       131.2
09:20       19.7       133.3
09:30       21.1       135.4
09:40       22.3       137.7
09:50       23.5       139.9
10:00       24.7       142.3
10:10       25.8       144.6
10:20       26.8       147.1
10:30       27.8       149.6
10:40       28.7       152.1
10:50       29.5       154.7
11:00       30.3       157.4
11:10       30.9       160.1
11:20       31.5       162.8
11:30       32.0       165.6
11:40       32.5       168.4
11:50       32.8       171.3
12:00       33.0       174.2
12:10       33.2       177.0
12:20       33.2       179.9
12:30       33.2       182.8
12:40       33.0       185.7
12:50       32.8       188.6
13:00       32.5       191.4
13:10       32.1       194.3
13:20       31.6       197.1
13:30       31.0       199.8
13:40       30.3       202.5
13:50       29.6       205.2
14:00       28.8       207.8
14:10       27.9       210.3
14:20       26.9       212.8
14:30       25.9       215.3
14:40       24.8       217.7
14:50       23.6       220.0
15:00       22.4       222.3
15:10       21.2       224.5
15:20       19.9       226.7
15:30       18.5       228.8
15:40       17.1       230.9
15:50       15.7       232.9
16:00       14.2       234.9
16:10       12.7       236.8
16:20       11.1       238.7
16:30        9.5       240.6
16:40        7.9       242.4
16:50        6.3       244.2
17:00        4.7       245.9
17:10        3.0       247.7
17:20        1.4       249.4
17:30       -0.1       251.1
17:40       -2.4       252.7
17:50       -4.2       254.4
18:00       -5.9       256.1
18:10       -7.7       257.7
18:20       -9.6       259.3
18:30      -11.4       261.0
'''


_ITHACA_MOON_TABLE = '''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
ITHACA, NY                                                                    
   o  ,    o  ,                                                               
W 76 30, N42 27
                                                              
Altitude and Azimuth of the Moon                                              
Feb 10, 2016
                                                                 
Zone:  5h West of Greenwich
                                                  
          Altitude    Azimuth    Fraction                                     
                      (E of N)  Illuminated
                                  
 h  m         o           o                                                   
                                                                              
                                                                              
07:20      -11.0        87.3       0.05
07:30       -9.2        88.9       0.05
07:40       -7.4        90.5       0.05
07:50       -5.6        92.1       0.05
08:00       -3.8        93.7       0.05
08:10       -2.0        95.3       0.05
08:20        0.3        96.9       0.05
08:30        1.9        98.5       0.05
08:40        3.5       100.1       0.05
08:50        5.3       101.8       0.05
09:00        7.0       103.4       0.05
09:10        8.7       105.1       0.05
09:20       10.4       106.8       0.05
09:30       12.1       108.5       0.05
09:40       13.8       110.3       0.05
09:50       15.5       112.0       0.06
10:00       17.2       113.9       0.06
10:10       18.8       115.7       0.06
10:20       20.4       117.6       0.06
10:30       22.0       119.6       0.06
10:40       23.6       121.6       0.06
10:50       25.1       123.6       0.06
11:00       26.6       125.7       0.06
11:10       28.1       127.9       0.06
11:20       29.5       130.2       0.06
11:30       30.9       132.5       0.06
11:40       32.2       134.9       0.06
11:50       33.5       137.3       0.06
12:00       34.7       139.9       0.06
12:10       35.8       142.5       0.06
12:20       36.9       145.2       0.06
12:30       37.9       148.0       0.06
12:40       38.9       150.8       0.06
12:50       39.7       153.7       0.06
13:00       40.5       156.8       0.06
13:10       41.2       159.8       0.06
13:20       41.8       163.0       0.06
13:30       42.3       166.2       0.06
13:40       42.7       169.5       0.06
13:50       43.1       172.7       0.06
14:00       43.3       176.1       0.06
14:10       43.4       179.4       0.07
14:20       43.4       182.8       0.07
14:30       43.3       186.1       0.07
14:40       43.0       189.4       0.07
14:50       42.7       192.7       0.07
15:00       42.3       196.0       0.07
15:10       41.8       199.2       0.07
15:20       41.2       202.3       0.07
15:30       40.5       205.4       0.07
15:40       39.7       208.4       0.07
15:50       38.8       211.4       0.07
16:00       37.9       214.2       0.07
16:10       36.9       217.0       0.07
16:20       35.8       219.7       0.07
16:30       34.7       222.3       0.07
16:40       33.4       224.9       0.07
16:50       32.2       227.3       0.07
17:00       30.9       229.7       0.07
17:10       29.5       232.1       0.07
17:20       28.1       234.3       0.07
17:30       26.6       236.5       0.07
17:40       25.2       238.6       0.07
17:50       23.6       240.7       0.07
18:00       22.1       242.7       0.08
18:10       20.5       244.7       0.08
18:20       18.9       246.6       0.08
18:30       17.3       248.5       0.08
18:40       15.6       250.3       0.08
18:50       14.0       252.2       0.08
19:00       12.3       253.9       0.08
19:10       10.6       255.7       0.08
19:20        8.9       257.4       0.08
19:30        7.2       259.1       0.08
19:40        5.5       260.8       0.08
19:50        3.8       262.5       0.08
20:00        2.2       264.1       0.08
20:10        0.6       265.8       0.08
20:20       -1.6       267.5       0.08
20:30       -3.4       269.1       0.08
20:40       -5.1       270.8       0.08
20:50       -6.9       272.4       0.08
21:00       -8.6       274.1       0.08
21:10      -10.4       275.7       0.08
'''
