import datetime
import numpy as np
import os
import unittest

from nfc.archive.archive import Archive
from nfc.util.bunch import Bunch


ARCHIVE_DIR_PATH = ['data', 'Test Archive']

STATION_NAMES = ['A', 'B']
STATIONS = [Bunch(name=n) for n in STATION_NAMES]

DETECTOR_NAMES = ['Tseep', 'Thrush']
DETECTORS = [Bunch(name=n) for n in DETECTOR_NAMES]

CLIP_CLASS_NAMES = ['X', 'X.Z', 'X.Z.W', 'Y']
CLIP_CLASSES = [Bunch(name=n) for n in CLIP_CLASS_NAMES]


class ArchiveTests(unittest.TestCase):
    
    
    def setUp(self):
        parent_dir_path = os.path.dirname(__file__)
        archive_dir_path = os.path.join(parent_dir_path, *ARCHIVE_DIR_PATH)
        self.archive = Archive.create(
            archive_dir_path, STATIONS, DETECTORS, CLIP_CLASSES)
        
        
    def tearDown(self):
        self.archive.close()
        
        
    def test_add_clip(self):
        self._add_clips()
        
        
    def _add_clips(self):
        
        clips = self._add_clips_aux(
            ('A', 'Tseep', 2012, 1, 2, 20, 11, 12, 0),
            ('A', 'Tseep', 2012, 1, 3, 2, 11, 12, 100),
            ('A', 'Tseep', 2012, 1, 3, 20, 13, 14, 0),
            ('A', 'Thrush', 2012, 1, 2, 20, 11, 13, 0),
            ('B', 'Tseep', 2012, 1, 2, 20, 11, 14, 0)
        )
        
        classifications = (
            (0, 'X'),
            (1, 'Y'),
            (2, 'X.Z'),
            (3, 'X'),
            (0, 'X.Z.W'))
        
        for (i, clip_class_name) in classifications:
            clips[i].clip_class_name = clip_class_name

               
    def _add_clips_aux(self, *args):
        return [self._add_clip(*a) for a in args]
    
    
    def _add_clip(
        self, station_name, detector_name,
        year, month, day, hour, minute, second, ms):
        
        time = datetime.datetime(
                   year, month, day, hour, minute, second, ms * 1000)
        
        sound = Bunch(samples=np.zeros(100), sample_rate=22050.)
        
        return self.archive.add_clip(station_name, detector_name, time, sound)

    
    def test_get_stations(self):
        stations = self.archive.get_stations()
        attribute_names = ('id', 'name')
        expected_values = [(i + 1, STATION_NAMES[i])
                           for i in xrange(len(STATION_NAMES))]
        self._assert_bunches(stations, attribute_names, expected_values)
        
        
    def _assert_bunches(self, bunches, attribute_names, expected_values):
        
        self.assertEqual(len(bunches), len(expected_values))
        
        for (bunch, values) in zip(bunches, expected_values):
            
            self.assertIsInstance(bunch, Bunch)
            
            for (i, name) in enumerate(attribute_names):
                self.assertEqual(getattr(bunch, name), values[i])


    def test_get_detectors(self):
        detectors = self.archive.get_detectors()
        attribute_names = ('id', 'name')
        expected_values = [(i + 1, DETECTOR_NAMES[i])
                           for i in xrange(len(DETECTOR_NAMES))]
        self._assert_bunches(detectors, attribute_names, expected_values)
        
        
    def test_get_clip_classes(self):
        clip_classes = self.archive.get_clip_classes()
        attribute_names = ('id', 'name')
        expected_values = [(i + 1, CLIP_CLASS_NAMES[i])
                           for i in xrange(len(CLIP_CLASS_NAMES))]
        self._assert_bunches(clip_classes, attribute_names, expected_values)
        
        
    def test_get_start_night(self):
        self._add_clips()
        night = self.archive.get_start_night()
        self.assertEquals(night, _to_date((2012, 1, 2)))
        
        
    def test_get_end_night(self):
        self._add_clips()
        night = self.archive.get_end_night()
        self.assertEquals(night, _to_date((2012, 1, 3)))
        
        
    def test_get_clip_counts(self):
        
        cases = (
                 
            (('A', 'Tseep'),
             {(2012, 1, 2): 2, (2012, 1, 3): 1}),
                 
            ((None, None, (2012, 1, 2), (2012, 1, 2)),
             {(2012, 1, 2): 4})
                 
        )
                
        self._add_clips()
        
        for (args, expected_result) in self._create_get_counts_cases(cases):
            result = self.archive.get_clip_counts(*args)
            self.assertEqual(result, expected_result)
        
        
    def _create_get_counts_cases(self, cases):
        return [self._create_get_counts_case(args, result)
                for (args, result) in cases]
    
    
    def _create_get_counts_case(self, args, result):
        return (self._create_get_counts_case_args(*args),
                self._create_get_counts_case_result(result))
            
            
    def _create_get_counts_case_args(
        self, station_name=None, detector_name=None,
        start_night=None, end_night=None, clip_class_name=None):
        
        return (station_name, detector_name,
                _to_date(start_night), _to_date(end_night), clip_class_name)
    
    
    def _create_get_counts_case_result(self, result):
        date = datetime.date
        return dict((date(*triple), count)
                    for (triple, count) in result.iteritems())
    
    
    def test_get_clips(self):
        
        cases = (
                 
            (('A', 'Tseep'),
             [('A', 'Tseep', 2012, 1, 2, 20, 11, 12, 0, 'X.Z.W'),
              ('A', 'Tseep', 2012, 1, 3, 2, 11, 12, 100000, 'Y'),
              ('A', 'Tseep', 2012, 1, 3, 20, 13, 14, 0, 'X.Z')]),
                 
            ((None, None, (2012, 1, 2)),
             [('A', 'Tseep', 2012, 1, 2, 20, 11, 12, 0, 'X.Z.W'),
              ('A', 'Thrush', 2012, 1, 2, 20, 11, 13, 0, 'X'),
              ('B', 'Tseep', 2012, 1, 2, 20, 11, 14, 0, None),
              ('A', 'Tseep', 2012, 1, 3, 2, 11, 12, 100000, 'Y')])

        )
        
#        classifications = (
#            (0, 'X'),
#            (1, 'Y'),
#            (2, 'X.Z'),
#            (3, 'X'),
#            (0, 'X.Z.W'))

        self._add_clips()
        
        for (args, expected_result) in self._create_get_clips_cases(cases):
            result = self.archive.get_clips(*args)
            self._check_get_clips_case_result(result, expected_result)

        
    def _create_get_clips_cases(self, cases):
        return [self._create_get_clips_case(args, result)
                for (args, result) in cases]
    
    
    def _create_get_clips_case(self, args, result):
        return (self._create_get_clips_case_args(*args), result)
            
            
    def _create_get_clips_case_args(
        self, station_name=None, detector_name=None, night=None,
        clip_class_name=None):
        
        return (station_name, detector_name, _to_date(night), clip_class_name)
    
    
    def _check_get_clips_case_result(self, result, expected_result):
        
        self.assertEqual(len(result), len(expected_result))
        
        for (r, er) in zip(result, expected_result):
            self.assertEqual(r.station_name, er[0])
            self.assertEqual(r.detector_name, er[1])
            self.assertEqual(r.time, datetime.datetime(*er[2:9]))
            self.assertEqual(r.clip_class_name, er[9])
    
    
    def test_zzz(self):
        self._add_clips()
        
        
#     def _assert_raises(self, exception_class, function, *args, **kwargs):
#
#         self.assertRaises(exception_class, function, *args, **kwargs)
#
#         try:
#             function(*args, **kwargs)
#
#         except exception_class, e:
#             print str(e)
            

def _to_date(triple):
    return datetime.date(*triple) if triple is not None else None
