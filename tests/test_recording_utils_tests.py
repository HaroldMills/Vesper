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
             [(_r('A', '2015-05-30 20:00:00', '10:00:00'), 1)]),
                  
            # two exactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:00', '06:00:00')],
             [(_r('A', '2015-05-30 20:00:00', '11:00:00'), 2)]),
                  
            # three exactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '01:00:00'),
              _r('A', '2015-05-30 21:00:00', '02:00:00'),
              _r('A', '2015-05-30 23:00:00', '03:00:00')],
             [(_r('A', '2015-05-30 20:00:00', '06:00:00'), 3)]),
                  
            # two inexactly consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:01', '06:00:00')],
             [(_r('A', '2015-05-30 20:00:00', '11:00:00'), 2)]),
                  
            # two barely non-consecutive recordings
            ([_r('A', '2015-05-30 20:00:00', '05:00:00'),
              _r('A', '2015-05-31 01:00:02', '06:00:00')],
             [(_r('A', '2015-05-30 20:00:00', '05:00:00'), 1),
              (_r('A', '2015-05-31 01:00:02', '06:00:00'), 1)]),
                 
            # four consecutive recordings from two stations
            ([_r('A', '2015-05-30 20:00:00', '01:00:00'),
              _r('A', '2015-05-30 21:00:00', '02:00:00'),
              _r('B', '2015-05-30 23:00:00', '03:00:00'),
              _r('B', '2015-05-31 02:00:00', '04:00:00')],
             [(_r('A', '2015-05-30 20:00:00', '03:00:00'), 2),
              (_r('B', '2015-05-30 23:00:00', '07:00:00'), 2)])
                 
        ]
        
        for recordings, expected in cases:
            result = recording_utils.merge_recordings(recordings)
            self._check_result(result, expected, recordings)
            
            
    def _check_result(self, result, expected, recordings):
        
        self.assertEqual(len(result), len(expected))
        
        i = 0
        
        for r, (e, n) in zip(result, expected):
            self._assert_recordings_equal(r, e)
            self._check_subrecordings(r, recordings, i, n)
            i += n
            
            
    def _assert_recordings_equal(self, a, b):
        self.assertEqual(a.station.name, b.station.name)
        self.assertEqual(a.start_time, b.start_time)
        self.assertEqual(a.length, b.length)
        self.assertEqual(a.sample_rate, b.sample_rate)
        
        
    def _check_subrecordings(self, r, recordings, i, n):
        s = r.subrecordings
        self.assertEqual(len(s), n)
        for j in range(n):
            self._assert_recordings_equal(s[j], recordings[i + j])
                
        
        
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
