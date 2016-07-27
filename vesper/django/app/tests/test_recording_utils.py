import datetime

from vesper.django.app.recording import Recording
from vesper.tests.test_case import TestCase
import vesper.django.app.recording_utils as recording_utils
import vesper.util.time_utils as time_utils


class RecordingUtilsTests(TestCase):
        
        
    def test_group_recording_files(self):
        
        r = create_recording
        
        cases = [
                 
            # single file
            ([r('A', '2015-05-30 20:00:00', '10:00:00')],
             [(r('A', '2015-05-30 20:00:00', '10:00:00'), 1)]),
                  
            # two exactly consecutive files
            ([r('A', '2015-05-30 20:00:00', '05:00:00'),
              r('A', '2015-05-31 01:00:00', '06:00:00')],
             [(r('A', '2015-05-30 20:00:00', '11:00:00'), 2)]),
                  
            # three exactly consecutive files
            ([r('A', '2015-05-30 20:00:00', '01:00:00'),
              r('A', '2015-05-30 21:00:00', '02:00:00'),
              r('A', '2015-05-30 23:00:00', '03:00:00')],
             [(r('A', '2015-05-30 20:00:00', '06:00:00'), 3)]),
                  
            # two barely consecutive files, assuming a grouping tolerance
            # of one second per hour
            ([r('A', '2015-05-30 20:00:00', '05:00:00'),
              r('A', '2015-05-31 01:00:05', '06:00:00')],
             [(r('A', '2015-05-30 20:00:00', '11:00:00'), 2)]),
                  
            # two barely non-consecutive files, assuming a grouping tolerance
            # of one second per hour
            ([r('A', '2015-05-30 20:00:00', '05:00:00'),
              r('A', '2015-05-31 01:00:06', '06:00:00')],
             [(r('A', '2015-05-30 20:00:00', '05:00:00'), 1),
              (r('A', '2015-05-31 01:00:06', '06:00:00'), 1)]),
                 
            # two consecutive short files with a one-second error in
            # the second file's start time
            ([r('A', '2015-05-30 20:00:00', '00:01:00'),
              r('A', '2015-05-30 20:00:59', '00:01:00')],
             [(r('A', '2015-05-30 20:00:00', '00:02:00'), 2)]),
            
            # two non-consecutive files with a two-second error in the
            # second file's start time
            ([r('A', '2015-05-30 20:00:00', '00:01:00'),
              r('A', '2015-05-30 20:01:02', '00:01:00')],
             [(r('A', '2015-05-30 20:00:00', '00:01:00'), 1),
              (r('A', '2015-05-30 20:01:02', '00:01:00'), 1)]),
                 
            # four consecutive files from two stations
            ([r('A', '2015-05-30 20:00:00', '01:00:00'),
              r('A', '2015-05-30 21:00:00', '02:00:00'),
              r('B', '2015-05-30 23:00:00', '03:00:00'),
              r('B', '2015-05-31 02:00:00', '04:00:00')],
             [(r('A', '2015-05-30 20:00:00', '03:00:00'), 2),
              (r('B', '2015-05-30 23:00:00', '07:00:00'), 2)]),
                 
            # two consecutive files with different numbers of channels
            ([r('A', '2015-05-30 20:00:00', '05:00:00', 1),
              r('A', '2015-05-31 01:00:00', '06:00:00', 2)],
             [(r('A', '2015-05-30 20:00:00', '05:00:00', 1), 1),
              (r('A', '2015-05-31 01:00:00', '06:00:00', 2), 1)]),
                 
            # two consecutive files with different sample rates
            ([r('A', '2015-05-30 20:00:00', '05:00:00', 1, 22050),
              r('A', '2015-05-31 01:00:00', '06:00:00', 1, 24000)],
             [(r('A', '2015-05-30 20:00:00', '05:00:00', 1, 22050), 1),
              (r('A', '2015-05-31 01:00:00', '06:00:00', 1, 24000), 1)]),
                 
        ]
        
        for files, expected in cases:
            result = recording_utils.group_recording_files(files)
            self._check_result(result, expected, files)
            
            
    def _check_result(self, result, expected, files):
        
        self.assertEqual(len(result), len(expected))
        
        i = 0
        
        for r, (e, n) in zip(result, expected):
            self._assert_recordings_equal(r, e)
            self._check_files(r, files, i, n)
            i += n
            
            
    def _assert_recordings_equal(self, a, b):
        self.assertEqual(a.station_name, b.station_name)
        # self.assertEqual(a.num_channels, b.num_channels)
        self.assertEqual(a.length, b.length)
        self.assertEqual(a.sample_rate, b.sample_rate)
        self.assertEqual(a.start_time, b.start_time)
        
        
    def _check_files(self, r, files, i, n):
        f = r.files
        self.assertEqual(len(f), n)
        for j in range(n):
            self._assert_recordings_equal(f[j], files[i + j])
                
        
        
def create_recording(
        station_name, start_time, duration, num_channels=1, sample_rate=22050):
    
    t = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    start_time = time_utils.create_utc_datetime(
        t.year, t.month, t.day, t.hour, t.minute, t.second)
    
    h, m, s = duration.split(':')
    delta = datetime.timedelta(hours=int(h), minutes=int(m), seconds=int(s))
    duration = delta.total_seconds()
    length = duration * sample_rate
    
    return Recording(
        station_name, num_channels, length, sample_rate, start_time)
