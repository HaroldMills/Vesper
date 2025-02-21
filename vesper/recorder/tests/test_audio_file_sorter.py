from datetime import datetime as DateTime
from pathlib import Path
import zoneinfo

from vesper.recorder.audio_file_writer import _AudioFileSorter
from vesper.tests.test_case import TestCase


class AudioFileSorterTests(TestCase):


    def test_get_dir_path(self):
    
        station_name = 'Ludlow'
        station_time_zone = 'US/Eastern'

        # Recording UTC start time for which UTC day and local day differ.
        recording_start_time = _utc_datetime(2025, 5, 1, 1, 23, 45)

        # File start time for which local day and local night differ,
        # and for which all file start time sort dates differ from the
        # corresponding recording start time sort dates.
        file_start_time = _utc_datetime(2025, 5, 2, 7, 23, 45)
    
        cases = (

            # No recording subdirectories.
            ((), 'Recording Start Time', 'UTC Day', ()),

            # Recording name subdirectory.
            (('Recording Name',), 'Recording Start Time', 'UTC Day',
                 ('Ludlow_2025-05-01_01.23.45_Z',)),

            # Station name, year, month, and day subdirectories.
            (('Station Name', 'Year', 'Month', 'Day'), 'Recording Start Time',
                 'UTC Day', ('Ludlow', '2025', '05', '01',)),

            # Year-month and recording name subdirectories.
            (('Year-Month', 'Recording Name'), 'Recording Start Time',
                 'UTC Day', ('2025-05', 'Ludlow_2025-05-01_01.23.45_Z',)),

            # Station name, month-day, and recording name subdirectories.
            (('Station Name', 'Month-Day', 'Recording Name'),
                 'Recording Start Time', 'UTC Day',
                 ('Ludlow', '05-01', 'Ludlow_2025-05-01_01.23.45_Z',)),

            # Year, month, and day subdirectories, recording start time
            # sort time, and UTC day sort period.,
            (('Year', 'Month', 'Day'), 'Recording Start Time', 'UTC Day',
                 ('2025', '05', '01',)),

            # Year, month, and day subdirectories, recording start time
            # sort time, and local day sort period.
            (('Year', 'Month', 'Day'), 'Recording Start Time', 'Local Day',
                 ('2025', '04', '30',)),

            # Year, month, and day subdirectories, recording start time
            # sort time, and local night sort period.
            (('Year', 'Month', 'Day'), 'Recording Start Time', 'Local Night',
                 ('2025', '04', '30',)),

            # Year, month, and day subdirectories, file start time sort
            # time, and UTC day sort period.
            (('Year', 'Month', 'Day'), 'File Start Time', 'UTC Day',
                 ('2025', '05', '02',)),

            # Year, month, and day subdirectories, recording start time
            # sort time, and local day sort period.
            (('Year', 'Month', 'Day'), 'File Start Time', 'Local Day',
                 ('2025', '05', '02',)),

            # Year, month, and day subdirectories, recording start time
            # sort time, and local night sort period.
            (('Year', 'Month', 'Day'), 'File Start Time', 'Local Night',
                 ('2025', '05', '01',)),

        )
    
        for recording_subdirs, file_sort_time, file_sort_period, subdir_names \
                in cases:
            
            expected = Path(*subdir_names)

            sorter = _AudioFileSorter(
                station_name, station_time_zone, recording_start_time,
                recording_subdirs, file_sort_time, file_sort_period)
            
            dir_path = sorter.get_dir_path(file_start_time)

            self.assertEqual(dir_path, expected)


_UTC = zoneinfo.ZoneInfo('UTC')


def _utc_datetime(year, month, day, hour, minute, second):
    return DateTime(year, month, day, hour, minute, second, tzinfo=_UTC)
