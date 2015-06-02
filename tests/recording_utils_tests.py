import datetime

from vesper.archive.recording import Recording
from vesper.archive.station import Station
import vesper.archive.recording_utils as recording_utils
import vesper.util.time_utils as time_utils

from test_case import TestCase


class RecordingUtilsTests(TestCase):
        
        
    def test_merge_recordings(self):
        
        cases = [
                 
            # single recording
            ([_r('A', '2015-05-30 20:00:00', '10:00:00')],
             [_r('A', '2015-05-30 20:00:00', '10:00:00')]),
                 
            # two exactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:00', '05:00:00')],
             [_r('A', '2015-05-30 20:00:00', '10:00:00')]),
                 
            # three exactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '01:00:00'),
              _r('A', '2015-05-30 21:00:00', '01:00:00'),
              _r('A', '2015-05-30 22:00:00', '01:00:00')],
             [_r('A', '2015-05-30 20:00:00', '03:00:00')]),
                 
            # two inexactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:01', '05:00:00')],
             [_r('A', '2015-05-30 20:00:00', '10:00:00')]),
                 
            # two barely non-consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:02', '05:00:00')],
             [_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:02', '05:00:00')])
                 
        ]
        
        for unmerged, expected in cases:
            merged = recording_utils.merge_recordings(unmerged)
            self._assert_recording_lists_equal(merged, expected)
            
            
    def _assert_recording_lists_equal(self, a, b):
        if len(a) != len(b):
            raise AssertionError('Recording list lengths differ.')
        for ra, rb in zip(a, b):
            self._assert_recordings_equal(ra, rb)
            
            
    def _assert_recordings_equal(self, a, b):
        self.assertEqual(a.station.name, b.station.name)
        self.assertEqual(a.start_time, b.start_time)
        self.assertEqual(a.length, b.length)
        self.assertEqual(a.sample_rate, b.sample_rate)
        
        
def _r(station_name, start_time, duration):
    
    station = Station(station_name, '', 'US/Eastern')
    
    t = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    start_time = time_utils.create_utc_datetime(
        t.year, t.month, t.day, t.hour, t.minute, t.second,
        time_zone=station.time_zone)
    
    sample_rate = 22050.

    h, m, s = duration.split(':')
    delta = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    duration = delta.total_seconds()
    length = duration * sample_rate
    
    return Recording(station, start_time, length, sample_rate)
