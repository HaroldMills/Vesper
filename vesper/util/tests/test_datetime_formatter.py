from datetime import datetime as DateTime

from vesper.tests.test_case import TestCase
from vesper.util.datetime_formatter import DateTimeFormatter


class DateTimeFormatterTests(TestCase):
    
    
    def test_get_min_time_increment(self):
        
        get_increment = DateTimeFormatter.get_min_time_increment
        
        cases = (
            ('', None),
            ('Hello, world!', None),
            ('Hello, %% %%H %a %w %Y world!', None),
            ('%d', None),
            ('%H', 3600),
            ('%h', 3600),
            ('%I', 3600),
            ('%M', 60),
            ('%m', 60),
            ('%S', 1),
            ('%s', 1),
            ('%f', .000001),
            ('%1f', .1),
            ('%2f', .01),
            ('%3f', .001),
            ('%4f', .0001),
            ('%5f', .00001),
            ('%6f', .000001),
            ('Hello, %Y-%m-%d %H:%M:%S.%3f world!', .001),
            ('Hello, %d %% %G %3f world! %% %H %f', .000001),
        )
        
        for format_string, expected in cases:
            
            # via static method
            actual = get_increment(format_string)
            self.assertEqual(actual, expected)
            
            # via property
            formatter = DateTimeFormatter(format_string)
            actual = formatter.min_time_increment
            self.assertEqual(actual, expected)
    
    
    def test_format_datetime(self):
        
        dt = DateTime(2020, 1, 1, 12, 34, 59, 123456)
                
        cases = (
            
            # fractional second without digit count
            (dt, '%f', '123456'),
            
            # fractional second with digit count
            (dt, '%6f', '123456'),
            (dt, '%5f', '12345'),
            (dt, '%4f', '1234'),
            (dt, '%3f', '123'),
            (dt, '%2f', '12'),
            (dt, '%1f', '1'),
            
            # complete time, fractional second without digit count
            (dt, '%Y-%m-%d %H:%M:%S.%f', '2020-01-01 12:34:59.123456'),
            
            # complete time, fractional second with digit count
            (dt, '%Y-%m-%d %H:%M:%S.%6f', '2020-01-01 12:34:59.123456'),
            (dt, '%Y-%m-%d %H:%M:%S.%5f', '2020-01-01 12:34:59.12345'),
            (dt, '%Y-%m-%d %H:%M:%S.%4f', '2020-01-01 12:34:59.1234'),
            (dt, '%Y-%m-%d %H:%M:%S.%3f', '2020-01-01 12:34:59.123'),
            (dt, '%Y-%m-%d %H:%M:%S.%2f', '2020-01-01 12:34:59.12'),
            (dt, '%Y-%m-%d %H:%M:%S.%1f', '2020-01-01 12:34:59.1'),
            
            # miscellaneous (non-locale-specific, so case should work
            # anywhere) format codes
            (dt, '%U %j %w %%', '00 001 3 %'),
            
            # tricky cases
            (dt, '%%%%', '%%'),
            (dt, '%%3f', '%3f'),
            (dt, '%%%3f', '%123'),
            (dt, '%%3f%3f', '%3f123'),
            (dt, '%%3f%%%3f', '%3f%123'),
            (dt, '%% %1f %% %2f %% %3f %4f %%', '% 1 % 12 % 123 1234 %'),
            
        )
        
        for dt, format_string, expected in cases:
            formatter = DateTimeFormatter(format_string)
            actual = formatter.format(dt)
            self.assertEqual(actual, expected)
