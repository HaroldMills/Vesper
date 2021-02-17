from datetime import datetime as DateTime

from vesper.tests.test_case import TestCase
import vesper.util.text_utils as text_utils


class TextUtilsTests(TestCase):
    
    
    def test_create_string_item_list(self):
        
        cases = (
            ([], ''),
            (['one'], 'one'),
            (['one', 'two'], 'one and two'),
            (['one', 'two', 'three'], 'one, two, and three'),
            (['one', 'two', 'three', 'four'], 'one, two, three, and four'),
            ([1, 2, 3], '1, 2, and 3')
        )
        
        for items, expected in cases:
            result = text_utils.create_string_item_list(items)
            self.assertEqual(result, expected)
        
        
    def test_format_number(self):
        
        cases = [
                 
            # integers
            (0, '0'),
            (1, '1.0'),
            (9, '9.0'),
            (10, '10'),
            (99, '99'),
            (1234, '1234'),
            
            # floats
            (.0000000001, '0.00000000010'),
            (.00000000011, '0.00000000011'),
            (.123, '0.12'),
            (.125, '0.12'),
            (.12500001, '0.13'),
            (1.23, '1.2'),
            (1.25, '1.2'),
            (1.2500001, '1.3'),
            (9.49999, '9.5'),
            (9.5, '10'),
            (10.1, '10'),
            (1234.56, '1235')
            
        ]
        
        for x, expected in cases:
            result = text_utils.format_number(x)
            self.assertEqual(result, expected)
    
    
    def test_format_datetime(self):
        
        format_datetime = text_utils.format_datetime
        
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
        
        for dt, format_, expected in cases:
            actual = format_datetime(dt, format_)
            self.assertEqual(actual, expected)
    
    
    def test_format_time_difference(self):
        
        format_time_difference = text_utils.format_time_difference
        
        d12345 = 3600 + 23 * 60 + 45
        d123456 = 12 * 3600 + 34 * 60 + 56
        d1233456 = 123 * 3600 + 34 * 60 + 56
        d12345p4 = d12345 + .4
        d12345p6 = d12345 + .6
        d12345p678 = d12345 + .678
        d12345p9999 = d12345 + .9999
        
        # default format cases
        cases = (
            
            # Default format, zero.
            (0, '0:00:00'),
            
            # Default format, positive.
            (1, '0:00:01'),
            (d12345, '1:23:45'),
            (d123456, '12:34:56'),
            (d1233456, '123:34:56'),
            (d12345p4, '1:23:45'),
            (d12345p6, '1:23:46'),
            
            # Default format, negative.
            # Default format, positive.
            (-1, '-0:00:01'),
            (-d12345, '-1:23:45'),
            (-d123456, '-12:34:56'),
            (-d1233456, '-123:34:56'),
            (-d12345p4, '-1:23:45'),
            (-d12345p6, '-1:23:46'),
        
        )
        
        for seconds, expected in cases:
            actual = format_time_difference(seconds)
            self.assertEqual(actual, expected)
        
        # non-default format with positional arguments
        cases = (
            
            (0, (None, 3), '0:00:00.000'),
            (0, (2,), '00:00:00'),
            (0, (2, 3), '00:00:00.000'),
            
            (d12345p678, (None, 3), '1:23:45.678'),
            (d12345p678, (2,), '01:23:46'),
            (d12345p678, (2, 3), '01:23:45.678'),
            
            # more digits in hours than specified via `hours_digit_count`
            (d1233456, (2,), '123:34:56'),
        
        )
        
        for seconds, args, expected in cases:
            actual = format_time_difference(seconds, *args)
            self.assertEqual(actual, expected)
        
        # non-default format with positional and keyword arguments
        cases = (
            
            (d12345p678, (), {'fraction_digit_count': 1}, '1:23:45.7'),
            (d12345p678, (2,), {'fraction_digit_count': 1}, '01:23:45.7'),
            (d12345p678, (3,), {'fraction_digit_count': 2}, '001:23:45.68'),
            
            # rounding affects multiple digits
            (d12345p9999, (),
             {'hours_digit_count': 2, 'fraction_digit_count': 3},
             '01:23:46.000')
        
        )
        
        for seconds, args, kwargs, expected in cases:
            actual = format_time_difference(seconds, *args, **kwargs)
            self.assertEqual(actual, expected)
