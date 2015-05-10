from test_case import TestCase
import datetime

import mpg_ranch.importer as importer


'''
    _CSD + 'time6 dur6 detector elapsed7 num2',
    _CSD + 'time6 dur6 detector elapsed7',
    _CSD + 'time4 dur4 detector elapsed7 num2',
    _CSD + 'time4 dur4 detector elapsed7',
    _CSD + 'time6 detector elapsed7 num2',
    _CSD + 'time4 detector elapsed7 num2',
    _CSD + 'time4 detector elapsed7',
    _CSD + 'time4 detector elapsed6',
    _CSD + 'time6 dur6 second_dur detector elapsed7 num2',
    _CSD + 'time6 dur6 interior_comment second_dur detector elapsed7 num2',
    _CSD + 'time6 dur6 interior_comment detector elapsed7 num2',
'''
    
    
_STATION_NAMES = ['baldy', 'flood', 'ridge', 'sheep']
_DETECTOR_NAMES = ['Manual', 'Tseep', 'Thrush']
_CLIP_CLASS_NAMES = ['unkn', 'wiwa']
_COMMENTS = [None, 'comment', 'comment_with_underscores']
_CASES = [
    ('191234_081234', '001.23.45_12',
        (19, 12, 34), (8, 12, 34), None, None, (1, 23, 45), 12),
    ('191234_081234', '001.23.45',
        (19, 12, 34), (8, 12, 34), None, None, (1, 23, 45), None),
    ('1912_0812', '001.23.45_12',
        (19, 12, 0), (8, 12, 0), None, None, (1, 23, 45), 12),
    ('1912_0812', '001.23.45',
        (19, 12, 0), (8, 12, 0), None, None, (1, 23, 45), None),
    ('191234', '001.23.45_12',
        (19, 12, 34), None, None, None, (1, 23, 45), 12),
    ('1912', '001.23.45_12',
        (19, 12, 00), None, None, None, (1, 23, 45), 12),
    ('1912', '012345',
        (19, 12, 00), None, None, None, (1, 23, 45), None),
    ('191234_081234_123456', '001.23.45_12',
        (19, 12, 34), (8, 12, 34), None, (12, 34, 56), (1, 23, 45), 12),
    ('191234_081234_interior_comment_123456', '001.23.45_12',
        (19, 12, 34), (8, 12, 34), 'interior_comment', (12, 34, 56),
        (1, 23, 45), 12),
    ('191234_081234_interior_comment', '001.23.45_12',
        (19, 12, 34), (8, 12, 34), 'interior_comment', None, (1, 23, 45), 12)
]


class MpgRanchArchiverTests(TestCase):
    
    
    def test_parse_file_name(self):
        for station_name in _STATION_NAMES:
            for detector_name in _DETECTOR_NAMES:
                for clip_class_name in _CLIP_CLASS_NAMES:
                    for comment in _COMMENTS:
                        for case in _CASES:
                            self._test_parse_file_name(
                                station_name, detector_name, clip_class_name,
                                comment, *case)
            
            
    def _test_parse_file_name(
            self, station_name, detector_name, clip_class_name, comment,
            name_a, name_b, time, dur, mcomment, mdur, clip_time, clip_num):
        
        name_a = '_' + name_a if name_a is not None else ''
        suffix = '_' + comment if comment is not None else ''
        file_name = '{:s}_{:s}_030915{:s}_{:s}_{:s}{:s}.wav'.format(
            clip_class_name, station_name, name_a, detector_name, name_b,
            suffix)
        
        result = importer._parse_file_name(file_name)
        
        expected_result = importer._ClipInfo(
            station_name.capitalize(), detector_name.capitalize(),
            _date(2015, 3, 9), _time(*time), _delta(dur),
            mcomment, _delta(mdur),
            _delta(clip_time), clip_num, clip_class_name,
            comment
        )
        
        self.assertEqual(result, expected_result)


_date = datetime.date
_time = datetime.time


def _delta(d):
    if d is None:
        return None
    else:
        h, m, s = d
        return datetime.timedelta(hours=h, minutes=m, seconds=s)
