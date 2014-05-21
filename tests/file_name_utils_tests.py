import datetime
import unittest

import old_bird.file_name_utils as file_name_utils


class ClipFileNameUtilsTests(unittest.TestCase):
    
    
    def test_is_clip_file(self):
        fnu = file_name_utils
        self.assertTrue(fnu.is_clip_file_name('bobo.wav'))
        self.assertFalse(fnu.is_clip_file_name('bobo.aif'))
        self.assertFalse(fnu.is_clip_file_name('bobo.wavx'))
        
        
    def test_parse_absolute_clip_file_name(self):
        
        cases = [
                 
            ('Tseep_1900-01-02_12.34.56_07.wav',
             ('Tseep', 1900, 1, 2, 12, 34, 56, 7)),
                 
            ('Tseep_2013-01-02_12.34.56_07.wav',
             ('Tseep', 2013, 1, 2, 12, 34, 56, 7)),
                 
            ('Tseep_2012-01-02_12.34.56_07.wav',
             ('Tseep', 2012, 1, 2, 12, 34, 56, 7)),
                 
            ('Tseep_2012-02-29_12.34.56_07.wav',
             ('Tseep', 2012, 2, 29, 12, 34, 56, 7)),
                 
        ]
        
        parse = file_name_utils.parse_absolute_clip_file_name
        check = self._assert_time
        self._test_parse_clip_file_name(cases, parse, check)
        
        
    def _test_parse_clip_file_name(self, cases, parse, check):
        for file_name, expected_result in cases:
            (detector_name, time) = parse(file_name)
            self.assertEqual(detector_name, expected_result[0])
            check(time, expected_result[1:])
            
            
    def _assert_time(self, time, expected):
        
        (year, month, day, hour, minute, second, num) = expected
            
        expected_time = datetime.datetime(
            year, month, day, hour, minute, second, num * 100000)
        
        self.assertEqual(time, expected_time)
        
        
    def test_parse_absolute_clip_file_name_errors(self):
        
        next_year = datetime.datetime.now().year + 1
        
        cases = [
                 
            # malformed
            'Bobo',
            
            # stray separators
            'Tseep__2012-01-02_12.34.56_07.wav',
            'Tseep_2012--01-02_12.34.56_07.wav',
            'Tseep_2012-01--02_12.34.56_07.wav',
            'Tseep_2012-01-02__12.34.56_07.wav',
            'Tseep_2012-01-02_12..34.56_07.wav',
            'Tseep_2012-01-02_12.34..56_07.wav',
            'Tseep_2012-01-02_12.34.56__07..wav',
            'Tseep_-2012-01-02_12.34.56_07.wav',
            'Tseep_20_12-01-02_12.34.56_07.wav',
            'Tseep_2012-01-0-2_12.34.56_07.wav',
            'Tseep_2012-01-02_12.34.56_07_.wav',
             
            # non-digits in numbers
            'Tseep_201x-01-02_12.34.56_07.wav',
            'Tseep_2012-0x-02_12.34.56_07.wav',
            'Tseep_2012-01-0x_12.34.56_07.wav',
            'Tseep_2012-01-02_1x.34.56_07.wav',
            'Tseep_2012-01-02_12.3x.56_07.wav',
            'Tseep_2012-01-02_12.34.5x_07.wav',
            'Tseep_2012-01-02_12.34.56_xx.wav',
             
            # wrong numbers of digits in numbers
            'Tseep_02012-01-02_12.34.56_07.wav',
            'Tseep_2012-001-02_12.34.56_07.wav',
            'Tseep_2012-01-002_12.34.56_07.wav',
            'Tseep_2012-01-02_012.34.56_07.wav',
            'Tseep_2012-01-02_12.034.056_07.wav',
            'Tseep_2012-01-02_12.34.56_007.wav',
  
            # bad extension
            'Tseep_2012-01-02_12.34.56_07.aif',
    
            # year out of range
            'Tseep_1899-01-02_12.34.56_07.wav',
 
            # month out of range
            'Tseep_2012-00-02_12.34.56_07.wav',
            'Tseep_2012-13-02_12.34.56_07.wav',
              
            # day out of range
            'Tseep_2012-01-00_12.34.56_07.wav',
            'Tseep_2012-01-32_12.34.56_07.wav',
            'Tseep_2011-02-29_12.34.56_07.wav',
            'Tseep_2012-02-30_12.34.56_07.wav',
            'Tseep_2012-04-31_12.34.56_07.wav',
               
            # hour out of range
            'Tseep_2012-01-02_25.34.56_07.wav',
               
            # minute out of range
            'Tseep_2012-01-02_12.60.56_07.wav',
               
            # second out of range
            'Tseep_2012-01-02_12.34.60_07.wav',
            
        ]
        
        function = file_name_utils.parse_absolute_clip_file_name
        for file_name in cases:
            self._assert_raises(ValueError, function, file_name)

               
    def test_parse_relative_clip_file_name(self):
        
        cases = [
            ('Tseep_123.45.56_05.wav', ('Tseep', 123, 45, 56, 5)),
        ]
        
        parse = file_name_utils.parse_relative_clip_file_name
        check = self._assert_time_delta
        self._test_parse_clip_file_name(cases, parse, check)
            
            
    def _assert_time_delta(self, delta, expected):
        
        (hours, minutes, seconds, num) = expected
            
        microseconds = (num * 100000) / 1000000.
        total_seconds = hours * 3600 + minutes * 60 + seconds + microseconds
        
        self.assertEqual(delta.total_seconds(), total_seconds)
        
        
    def test_parse_relative_clip_file_name_errors(self):
        
        cases = [
                 
            # malformed
            'Bobo',
             
            # stray separators
            'Tseep__012.34.56_07.wav',
            'Tseep_012..34.56_07.wav',
            'Tseep_012.34..56_07.wav',
            'Tseep_012.34.56__07.wav',
            'Tseep_012.34.56_07..wav',
            'Tseep_-012.34.56_07.wav',
            'Tseep_012._34.56_07.wav',
            'Tseep_012.34.56_.07.wav',
            'Tseep_01_2.34.56_07.wav',
            'Tseep_012.34.56_07_8.wav',
             
            # non-digits in numbers
            'Tseep_01x.34.56_07.wav',
            'Tseep_012.3x.56_07.wav',
            'Tseep_012.34.5x_07.wav',
            'Tseep_012.34.56_xx.wav',
 
            # wrong numbers of digits in numbers
            'Tseep_0012.34.56_07.wav',
            'Tseep_012.034.56_07.wav',
            'Tseep_012.34.056_07.wav',
            'Tseep_012.34.56_7.wav',
 
            # bad extension
            'Tseep_012.34.56_07.aif',
             
            # minutes out of range
            'Tseep_012.60.56_07.wav',
             
            # seconds out of range
            'Tseep_012.34.60_07.wav',
            
        ]
        
        function = file_name_utils.parse_relative_clip_file_name
        for file_name in cases:
            self._assert_raises(ValueError, function, file_name)

               
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class, e:
            print str(e)
