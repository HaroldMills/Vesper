import datetime

from vesper.tests.test_case import TestCase
import vesper.old_bird.clip_import_utils as clip_import_utils


def _dt(year, month, day, hour, minute, second, tenths):
    microsecond = 100000 * tenths
    return datetime.datetime(
        year, month, day, hour, minute, second, microsecond)
    
    
class ClipImporterTests(TestCase):


    def test_parse_clip_file_name(self):
        
        cases = [
            
            ('Tseep_2017-08-01_12.34.56_00.wav',
             'Tseep', (2017, 8, 1, 12, 34, 56, 0)),
                 
            ('Thrush_2017-08-01_12.34.56_01.wav',
             'Thrush', (2017, 8, 1, 12, 34, 56, 1))
                 
        ]
        
        parse = clip_import_utils.parse_clip_file_name
        
        for file_name, expected_detector_name, expected_start_time in cases:
            
            detector_name, start_time = parse(file_name)
            
            self.assertEqual(detector_name, expected_detector_name)
            
            expected_start_time = _dt(*expected_start_time)
            self.assertEqual(start_time, expected_start_time)
            
            
    def test_parse_clip_file_name_errors(self):
        
        cases = [
        
            # don't match regular expression
            'bobo.wav',
            'Tseep_2017-08-01_12.34.56.wav',
            'Tseep_2017-08-01_12.34.56_aa.wav',
            
            # bad month
            'Tseep_2017-13-01_12.34.56_00.wav',
            
            # bad second
            'Tseep_2017-08-01_12.34.99_00.wav',

        ]
        
        parse = clip_import_utils.parse_clip_file_name
        
        for file_name in cases:
            self._assert_raises(ValueError, parse, file_name)
