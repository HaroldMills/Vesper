import datetime
import numpy as np
import os
import shutil

from vesper.archive.archive import Archive
from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.station import Station
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


ARCHIVE_NAME = 'Test Archive'
ARCHIVE_DIR_PATH = ['data', ARCHIVE_NAME]

STATION_TUPLES = [
    ('A', 'Station A', 'US/Eastern', 42.4, -76.5, 120.),
    ('B', 'Station B', 'America/Mexico_City', 42.5, -76.6, 130.)
]
STATIONS = [Station(*t) for t in STATION_TUPLES]

DETECTOR_NAMES = ['Tseep', 'Thrush']
DETECTORS = [Detector(name=n) for n in DETECTOR_NAMES]

CLIP_CLASS_NAMES = ['X', 'X.Z', 'X.Z.W', 'Y']
CLIP_CLASSES = [ClipClass(name=n) for n in CLIP_CLASS_NAMES]

RECORDING_TUPLES = [
    ('A', 2012, 5, 19, 19, 11, 12, 0, 100, 22050),
    ('A', 2015, 5, 20, 19, 11, 12, 0, 100, 22050),
    ('A', 2015, 5, 20, 20, 12, 13, 0, 200, 24000),
    ('A', 2015, 5, 21, 19, 12, 13, 100, 200, 24000),
    ('B', 2015, 5, 20, 19, 11, 12, 0, 100, 22050)
]


class ArchiveTests(TestCase):
    
    
    def setUp(self):
        parent_dir_path = os.path.dirname(__file__)
        archive_dir_path = os.path.join(parent_dir_path, *ARCHIVE_DIR_PATH)
        shutil.rmtree(archive_dir_path, ignore_errors=True)
        self.archive = Archive.create(
            archive_dir_path, STATIONS, DETECTORS, CLIP_CLASSES)
        self.archive.open()
        
        
    def tearDown(self):
        self.archive.close()
        
        
    def test_name(self):
        self.assertEqual(self.archive.name, ARCHIVE_NAME)
        
        
    def test_stations_property(self):
        stations = self.archive.stations
        attribute_names = (
            'id', 'name', 'long_name', 'latitude', 'longitude', 'elevation')
        expected_values = [
            ((i + 1,) + STATION_TUPLES[i][:2] + STATION_TUPLES[i][3:])
            for i in range(len(STATION_TUPLES))]
        expected_values.sort(key=lambda t: t[1])
        self._assert_objects(stations, attribute_names, expected_values)
        for i in range(len(STATION_TUPLES)):
            self.assertEqual(stations[i].time_zone.zone, STATION_TUPLES[i][2])
        
        
    def _assert_objects(self, objects, attribute_names, expected_values):
        
        self.assertEqual(len(objects), len(expected_values))
        
        for (obj, values) in zip(objects, expected_values):
            
            for (i, name) in enumerate(attribute_names):
                self.assertEqual(getattr(obj, name), values[i])


    def test_get_station(self):
        self._test_get_method(self.archive.get_station, 'A')
        
        
    def _test_get_method(self, method, name):
        obj = method(name)
        self.assertEqual(obj.name, name)
        self._assert_raises(ValueError, method, 'Bobo')
        
        
    def test_detectors_property(self):
        detectors = self.archive.detectors
        attribute_names = ('id', 'name')
        expected_values = [(i + 1, DETECTOR_NAMES[i])
                           for i in range(len(DETECTOR_NAMES))]
        expected_values.sort(key=lambda t: t[1])
        self._assert_objects(detectors, attribute_names, expected_values)
        
        
    def test_get_detector(self):
        self._test_get_method(self.archive.get_detector, 'Tseep')
        
        
    def test_clip_classes_property(self):
        clip_classes = self.archive.clip_classes
        attribute_names = ('id', 'name')
        expected_values = [(i + 1, CLIP_CLASS_NAMES[i])
                           for i in range(len(CLIP_CLASS_NAMES))]
        expected_values.sort(key=lambda t: t[1])
        self._assert_objects(clip_classes, attribute_names, expected_values)
        
        
    def test_get_clip_class(self):
        self._test_get_method(self.archive.get_clip_class, 'X')
        
        
    def test_start_night_property(self):
        self._add_clips()
        night = self.archive.start_night
        self.assertEqual(night, _to_date((2012, 1, 2)))
        
        
    def test_end_night_property(self):
        self._add_clips()
        night = self.archive.end_night
        self.assertEqual(night, _to_date((2012, 1, 3)))
        
        
    def test_add_recording(self):
        self._add_recordings()
        
        
    def _add_recordings(self):
        for r in RECORDING_TUPLES:
            self._add_recording(*r)
            
            
    def _add_recording(
            self, station_name, year, month, day, hour, minute, second, ms,
            length, sample_rate):
        
        start_time = time_utils.create_utc_datetime(
            year, month, day, hour, minute, second, ms * 1000, 'US/Eastern')
        
        self.archive.add_recording(
            station_name, start_time, length, sample_rate)
        
        
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
        
        start_time = time_utils.create_utc_datetime(
            year, month, day, hour, minute, second, ms * 1000)
        
        sound = Bunch(samples=np.zeros(100), sample_rate=22050.)
        
        return self.archive.add_clip(
            station_name, detector_name, start_time, sound)

    
    def test_get_recordings(self):
        self._add_recordings()
        night = _to_date((2015, 5, 20))
        recordings = self.archive.get_recordings('A', night)
        self.assertEqual(len(recordings), 2)
        for i, recording in enumerate(recordings):
            self._assert_recording(recording, *RECORDING_TUPLES[1 + i])
        
        
    def _assert_recording(
            self, recording, station_name, year, month, day, hour, minute,
            second, ms, length, sample_rate):
        
        self.assertEqual(recording.station.name, station_name)
        
        start_time = time_utils.create_utc_datetime(
            year, month, day, hour, minute, second, ms * 1000, 'US/Eastern')
        self.assertEqual(recording.start_time, start_time)
        
        self.assertEqual(recording.length, length)
        self.assertEqual(recording.sample_rate, sample_rate)
        
        
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
                    for (triple, count) in result.items())
    
    
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
            self.assertEqual(r.station.name, er[0])
            self.assertEqual(r.detector_name, er[1])
            start_time = time_utils.create_utc_datetime(*er[2:9])
            self.assertEqual(r.start_time, start_time)
            self.assertEqual(r.clip_class_name, er[9])
    
    
    def test_get_clip(self):
        
        cases = (
            ('A', 'Tseep', (2012, 1, 2, 20, 11, 12, 0), 'X.Z.W'),
            ('A', 'Tseep', (2014, 1, 1, 0, 0, 0, 0), None)
        )
        
        self._add_clips()
        
        for station_name, detector_name, time_tuple, expected_result in cases:
            
            start_time = time_utils.create_utc_datetime(*time_tuple)
            result = self.archive.get_clip(
                station_name, detector_name, start_time)
            
            if result is None:
                self.assertIsNone(expected_result)
                
            elif result.clip_class_name is None:
                self.assertEqual(expected_result, 'None')
                
            else:
                self.assertEqual(result.clip_class_name, expected_result)
        
        
#     def test_zzz(self):
#         self._add_clips()
        
        
def _to_date(triple):
    return datetime.date(*triple) if triple is not None else None
