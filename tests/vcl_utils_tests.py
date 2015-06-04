import datetime

from vesper.vcl.command import CommandSyntaxError
import vesper.vcl.vcl_utils as vcl_utils

from test_case import TestCase


class VclUtilsTests(TestCase):


    def test_get_station_names(self):
        self._test_get_object_names(
            'station', 'stations', vcl_utils.get_station_names)
        
        
    def _test_get_object_names(self, singular_name, plural_name, method):
        
        a = 'Name A'
        b = 'Name B'
        
        cases = [
            ({singular_name: (a,)}, (a,)),
            ({plural_name: (a,)}, (a,)),
            ({plural_name: (a, b)}, (a, b))
        ]
        
        for args, expected in cases:
            result = method(args)
            self.assertEqual(result, expected)
        
        
    def test_get_station_names_errors(self):
        self._test_get_object_names_errors(
            'station', 'stations', vcl_utils.get_station_names)
        
        
    def _test_get_object_names_errors(
            self, singular_name, plural_name, method):
        
        a = 'Name A'
        b = 'Name B'
        
        cases = [
                 
            # too few values
            {singular_name: ()},
            {plural_name: ()},
            
            # too many values
            {singular_name: (a, b)},
            
            # mutually exclusive keyword arguments
            {singular_name: (a,), plural_name: (b,)}
            
        ]
        
        for args in cases:
            self._assert_raises(CommandSyntaxError, method, args)
        
        
    def test_get_detector_names(self):
        self._test_get_object_names(
            'detector', 'detectors', vcl_utils.get_detector_names)
        
        
    def test_get_detector_names_errors(self):
        self._test_get_object_names_errors(
            'detector', 'detectors', vcl_utils.get_detector_names)
        
        
    def test_get_clip_class_names(self):
        self._test_get_object_names(
            'clip-class', 'clip-classes', vcl_utils.get_clip_class_names)
        
        
    def test_get_clip_class_names_errors(self):
        self._test_get_object_names_errors(
            'clip-class', 'clip-classes', vcl_utils.get_clip_class_names)
        
        
    def test_get_dates(self):
        
        d = _parse_date
        
        cases = [
            ({}, (None, None)),
            ({'date': ('2015-06-01',)}, ('2015-06-01', '2015-06-01')),
            ({'start-date': ('2015-06-01',)}, ('2015-06-01', None)),
            ({'end-date': ('2015-06-01',)}, (None, '2015-06-01')),
            ({'start-date': ('2015-06-01',), 'end-date': ('2015-06-01',)},
             ('2015-06-01', '2015-06-01')),
            ({'start-date': ('2015-06-01',), 'end-date': ('2015-06-10',)},
             ('2015-06-01', '2015-06-10'))
        ]
        
        for args, expected in cases:
            result = vcl_utils.get_dates(args)
            expected = (d(expected[0]), d(expected[1]))
            self.assertEqual(result, expected)
            
            
    def test_get_dates_errors(self):
        
        cases = [
                 
            {'date': ()},
            {'date': ('2015-06-01', '2015-06-02')},
            {'date': ('bobo',)},
            
            {'start-date': ()},
            {'start-date': ('2015-06-01', '2015-06-02')},
            {'start-date': ('bobo',)},
            
            {'end-date': ()},
            {'end-date': ('2015-06-01', '2015-06-02')},
            {'end-date': ('bobo',)},
            
            {'date': ('2015-06-01',), 'start-date': ('2015-06-01',)},
            {'date': ('2015-06-01',), 'end-date': ('2015-06-01',)},
            
            {'start-date': ('2015-06-01',), 'end-date': ('2015-05-31',)}
            
        ]
        
        for args in cases:
            self._assert_raises(CommandSyntaxError, vcl_utils.get_dates, args)
            
        
    def test_parse_date(self):
        
        cases = [
            (1900, 01, 01),
            (2099, 12, 31),
            (2014, 01, 02),
            (2014, 02, 28),
            (2012, 02, 29)
        ]
        
        for y, m, d in cases:
            s = '{:d}-{:02d}-{:02d}'.format(y, m, d)
            expected_result = datetime.date(y, m, d)
            result = vcl_utils.parse_date(s)
            self.assertEqual(result, expected_result)
            
            
    def test_parse_date_errors(self):
        
        cases = [
                 
            # bad characters
            'bobo',
            
            # wrong numbers of digits
            '1-01-01',
            '14-01-01',
            '12345-01-01',
            '2014-1-01',
            '2014-123-01',
            '2014-01-1',
            '2014-01-123',
            
            # values out of range
            '1899-12-31',
            '2100-01-01',
            '2014-00-01',
            '2014-13-01',
            '2014-01-00',
            '2014-01-32',
            '2014-02-29'
            
        ]
        
        for case in cases:
            self._assert_raises(
                CommandSyntaxError, vcl_utils.parse_date, case)


def _parse_date(date):
    if date is None:
        return date
    else:
        return vcl_utils.parse_date(date)
