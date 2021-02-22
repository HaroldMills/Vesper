from datetime import datetime as DateTime
import itertools

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
    
    
    def test_format_time_difference_g(self):
        
        cases = {
            
            'G': (
                (0, ''),
                (1, '+'),
                (-1, '-'),
            ),
            
            'g': (
                (0, ''),
                (1, ''),
                (-1, '-'),
            ),
        
        }
        
        keys = sorted(cases.keys())
        for key in keys:
            format_ = f'%{key}'
            for difference, expected in cases[key]:
                self._test_format_time_difference(
                    difference, format_, expected)
    
    
    def _test_format_time_difference(self, difference, format_, expected):
        # print(
        #     f'formatting {difference} with "{format_}", expecting '
        #     f'{expected}...')
        actual = text_utils.format_time_difference(difference, format_)
        self.assertEqual(actual, expected)
    
    
    def test_format_time_difference_dhms(self):
        
        seconds_per_second = 1
        seconds_per_minute = 60
        minutes_per_hour = 60
        hours_per_day = 24
        
        seconds_per_hour = minutes_per_hour * seconds_per_minute
        seconds_per_day = hours_per_day * seconds_per_hour
        
        test = self._test_dmhs_format
        test('d', seconds_per_day)
        test('h', seconds_per_hour)
        test('m', seconds_per_minute)
        test('s', seconds_per_second)
        test('H', seconds_per_hour, hours_per_day)
        test('M', seconds_per_minute, minutes_per_hour)
        test('S', seconds_per_second, seconds_per_minute)
    
    
    def _test_dmhs_format(self, letter, unit, modulus=None):
        cases = self._create_letter_cases([0, 1, 2, 10, 100], unit, modulus)
        self._test_letter_format(letter, cases)
    
    
    def _create_letter_cases(self, multipliers, unit, modulus):
        return itertools.chain.from_iterable(
            self._create_letter_cases_aux(m, unit, modulus)
            for m in multipliers)
    
    
    def _create_letter_cases_aux(self, multiplier, unit, modulus):
        
        difference = multiplier * unit
        epsilon = 1e-6
        
        differences = (
            difference - epsilon,
            difference,
            difference + epsilon,
            difference + .5 * unit,
        )
        
        # Discard any negative differences.
        differences = [d for d in differences if d >= 0]
        
        return [
            (d, self._get_letter_case_expected(d, unit, modulus))
            for d in differences]
    
    
    def _get_letter_case_expected(self, difference, unit, modulus):
        
        value = int(difference // unit)
        
        if modulus is None:
            # small letter
            
            return str(value)
        
        else:
            # capital letter
            
            value %= modulus
            return f'{value:02d}'
            
    
    def _test_letter_format(self, letter, cases):
        
        format_ = f'%{letter}'
        
        for difference, expected in cases:
            
            # non-negative difference
            self._test_format_time_difference(
                difference, format_, expected)
            
            # non-positive difference
            self._test_format_time_difference(
                -difference, format_, expected)


    def test_format_time_difference_f(self):
        cases = (0, .1, .12, .123, .1234, .12345, .123456)
        for difference in cases:
            for digit_count in range(7):
                test = self._test_format_time_difference_f
                test(difference, digit_count)
                test(-difference, digit_count)
    
    
    def _test_format_time_difference_f(self, difference, digit_count):
        
        format_ = text_utils.format_time_difference
        microseconds = str(int(abs(difference) * 1e6))
        
        if digit_count == 0:
            actual = format_(difference, '%f')
            expected = microseconds
        else:
            actual = format_(difference, f'%{digit_count}f')
            expected = microseconds[:digit_count]
        
        self.assertEqual(actual, expected)
        
    
    def test_format_time_difference_percent(self):
        actual = text_utils.format_time_difference(0, '%%')
        self.assertEqual(actual, '%')
    
    
    def test_format_time_difference_misc(self):
        
        day = 24 * 3600
        hour = 3600
        minute = 60
        
        f = 0.123456789
        d = 789 * day + 12 * hour + 34 * minute + 56 + f
        h = 789 * hour + 34 * minute + 56 + f
        m = 789 * minute + 56 + f
        s = 789 + f
 
        cases = (
            
            # various codes starting with "%d"
            (d, '%d:%H:%M:%S.%f', '789:12:34:56.123456'),
            (d, '%d:%H:%M:%S', '789:12:34:56'),
            (d, '%d:%H:%M', '789:12:34'),
            (d, '%d:%H', '789:12'),
            (d, '%d', '789'),
            
            # various codes starting with "%h"
            (h, '%h:%M:%S.%f', '789:34:56.123456'),
            (h, '%h:%M:%S', '789:34:56'),
            (h, '%h:%M', '789:34'),
            (h, '%h', '789'),
            
            # various codes starting with "%m"
            (m, '%m:%S.%f', '789:56.123456'),
            (m, '%m:%S', '789:56'),
            (m, '%m', '789'),
            
            # various codes starting with "%s"
            (s, '%s.%f', '789.123456'),
            (s, '%s', '789'),
            
            # multi-code formats with various numbers of fractional digits
            (d, '%d:%H:%M:%S.%1f', '789:12:34:56.1'),
            (d, '%d:%H:%M:%S.%2f', '789:12:34:56.12'),
            (d, '%d:%H:%M:%S.%3f', '789:12:34:56.123'),
            (d, '%d:%H:%M:%S.%4f', '789:12:34:56.1234'),
            (d, '%d:%H:%M:%S.%5f', '789:12:34:56.12345'),
            (d, '%d:%H:%M:%S.%6f', '789:12:34:56.123456'),
            
            # multi-code formats including signs
            (d, '%g%d:%H:%M:%S.%1f', '789:12:34:56.1'),
            (-d, '%g%d:%H:%M:%S.%1f', '-789:12:34:56.1'),
            (d, '%G%d:%H:%M:%S.%1f', '+789:12:34:56.1'),
            (-d, '%G%d:%H:%M:%S.%1f', '-789:12:34:56.1'),
            
            # repeated codes
            (d, '%d:%H:%M:%S.%1f %d:%H:%M:%S.%1f',
             '789:12:34:56.1 789:12:34:56.1'),
            
            # literal text
            (d, 'bobo %d:%H:%M:%S.%1f...', 'bobo 789:12:34:56.1...'),
            
            # unrecognized codes
            (d, '%x %0f %7f %8f %9f %10f', '%x %0f %7f %8f %9f %10f'),
            
            # unrecognized code mixed with recognized ones
            (d, '%d:%H:%M:%x%S.%1f', '789:12:34:%x56.1'),
            
        )
        
        for difference, format_, expected in cases:
            actual = text_utils.format_time_difference(difference, format_)
            self.assertEqual(actual, expected)
