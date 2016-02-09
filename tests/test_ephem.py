"""
Tests the PyEphem module for calculating sunrise and sunset times.

This script compares sunrise and sunset times as well as civil, nautical,
and astronomical dawn and dusk times computed by PyEphem to ones calculated
by the United States Naval Observatory (USNO). The tests use USNO tables
downloaded from http://aa.usno.navy.mil/data/docs/RS_OneYear.php by the
script `download_usno_sun_tables`. The tests compare thousands of times
computed for locations on a global grid for years from 1990 to 2030.
Test results are written to the CSV file "Rise Set Data.csv" and to the
text file "Big Differences.txt". The script `summarize_ephem_test_results`
computes some summary statistics from the test results.

For latitudes below the polar circles, the comparisons find no PyEphem
times that differ from the corresponding USNO times (the PyEphem times
are rounded to the nearest minute prior to comparison, since the USNO
times are rounded that way) by more than one minute. A small number of
PyEphem dawn and dusk times for locations above the polar circles
differ from the corresponding USNO times up to five minutes.
"""


from __future__ import print_function
from collections import defaultdict
import bisect
import calendar
import datetime
import os

import numpy as np
import pytz
import six

from vesper.util.usno_sun_moon_table import UsnoSunMoonTable
import vesper.util.astro_utils as astro_utils


_DATA_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\USNO Tables'
# _DATA_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/USNO Tables'
_CSV_FILE_NAME = 'Rise Set Data.csv'
_BIG_DIFFS_FILE_NAME = 'Big Differences.txt'

_OUTPUT_HEADER = (
    'Place Name,Table Type,Year,Latitude,Longitude,'
    'Risings Diff -2,Risings Diff -1,Risings Diff 0,Risings Diff 1,'
    'Risings Diff 2,Extra Ephem Risings,Extra USNO Risings,'
    'Settings Diff -2,Settings Diff -1,Settings Diff 0,Settings Diff 1,'
    'Settings Diff 2,Extra Ephem Settings,Extra USNO Settings')

_RISING_FUNCTIONS = {
    'Sunrise/Sunset': astro_utils.get_sunrise_time,
    'Civil Twilight': astro_utils.get_civil_dawn_time,
    'Nautical Twilight': astro_utils.get_nautical_dawn_time,
    'Astronomical Twilight': astro_utils.get_astronomical_dawn_time
}

_SETTING_FUNCTIONS = {
    'Sunrise/Sunset': astro_utils.get_sunset_time,
    'Civil Twilight': astro_utils.get_civil_dusk_time,
    'Nautical Twilight': astro_utils.get_nautical_dusk_time,
    'Astronomical Twilight': astro_utils.get_astronomical_dusk_time
}

_DISTINCT_EVENTS_DIFF = 10     # minutes
_BIG_DIFF = 2                  # minutes


_big_diffs = defaultdict(list)


def _main():
    
    csv_file_path = os.path.join(_DATA_DIR_PATH, _CSV_FILE_NAME)
    csv_file = open(csv_file_path, 'w')
    
    csv_file.write(_OUTPUT_HEADER + '\n')
    
    for dir_path, _, file_names in os.walk(_DATA_DIR_PATH):
        
        for file_name in file_names:
            
            if _is_table_file_name(file_name):
                
                print('comparing against file "{:s}"...'.format(file_name))
                
                file_path = os.path.join(dir_path, file_name)
                table = _read_table(file_path)
                
                place_name = os.path.basename(os.path.dirname(dir_path))
                
                line = _compare_against_table(table, place_name)
                
                if line is not None:
                    csv_file.write(line + '\n')
                    
            else:
                print('ignoring file "{:s}"'.format(file_name))
                
    csv_file.close()
    
    _write_big_diffs_file()
    
    print('done')
    
    
    print('See files "{:s}" and "{:s}" for results.'.format(
        _CSV_FILE_NAME, _BIG_DIFFS_FILE_NAME))
                
                
def _is_table_file_name(name):
    
    extension = '.txt'
    
    if not name.endswith(extension):
        return False
    
    name = name[:-len(extension)]
    parts = name.split('_')
    n = len(parts)
    
    return n == 4 or n == 5
    
    
def _read_table(path):
    
    with open(path, 'rU') as file_:
        text = file_.read()
        
    return UsnoSunMoonTable(text)
    
    
def _compare_against_table(table, place_name):
    
    year = table.year
    lat = table.lat
    lon = table.lon
    
    if table.type in _RISING_FUNCTIONS:

        function = _RISING_FUNCTIONS[table.type]
        times = _get_times(year, lat, lon, function)
        rising_diffs = _compare_times(times, table.rising_times, table)
        
        function = _SETTING_FUNCTIONS[table.type]
        times = _get_times(year, lat, lon, function)
        setting_diffs = _compare_times(times, table.setting_times, table)
        
        table_data = (table.type, year, lat, lon)
        data = (place_name,) + table_data + rising_diffs + setting_diffs
        line = ','.join(_format(d) for d in data)
        return line
        
                
def _get_times(year, lat, lon, function):
    
    times = []
    
    for month in xrange(1, 13):
        
        month_size = calendar.monthrange(year, month)[1]
        
        for day in xrange(1, month_size + 1):
            
            date = datetime.date(year, month, day)
            time = function(lat, lon, date)
            
            if time is not None:
                times.append(time)
                
    return times
            
            
def _compare_times(times, usno_times, table):
    
    global _big_diffs
    
    utc_offset = datetime.timedelta(hours=table.utc_offset)
    times = _round_times(times, utc_offset)
    usno_times = _round_times(usno_times, utc_offset)
    
    if len(times) != len(usno_times):
        return _compare_times_carefully(times, usno_times, table)
    
    else:
        # time sequences have same length
        
        diff_counts = np.zeros(2 * _BIG_DIFF + 1, dtype=np.int32)
        max_diff = -1000000
        min_diff = 1000000
        
        for time, usno_time in zip(times, usno_times):
            
            diff = _diff(time, usno_time)
            
            min_diff = min(diff, min_diff)
            max_diff = max(diff, max_diff)
            
            abs_diff = abs(diff)
            
            if abs_diff >= _DISTINCT_EVENTS_DIFF:
                return _compare_times_carefully(times, usno_times, table)
            
            elif abs(diff) >= _BIG_DIFF:
                _big_diffs[diff].append(
                    (table.type, table.lat, table.lon, time, usno_time))
                diff_counts[_sign(diff) * _BIG_DIFF] += 1
                
            else:
                diff_counts[diff] += 1
            
        diff_counts = _get_diff_counts_tuple(diff_counts)
        
        return diff_counts + (0, 0)


def _round_times(times, utc_offset):
    return [_round_datetime(time + utc_offset).replace(tzinfo=None)
            for time in times]


def _round_datetime(dt):
    rounded_time = datetime.datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, tzinfo=pytz.utc)
    seconds = dt.second + dt.microsecond / 1000000.
    if seconds > 30 or seconds == 30 and dt.minute % 2 == 1:
        rounded_time += datetime.timedelta(minutes=1)
    return rounded_time


def _compare_times_carefully(times, usno_times, table):
    
    diff_counts = np.zeros(2 * _BIG_DIFF + 1, dtype=np.int32)
    unmatched_times = []
    unmatched_usno_times = list(usno_times)
    
    for time in times:
        
        i = _find_time(time, unmatched_usno_times)
        
        if i != -1:
        
            usno_time = unmatched_usno_times[i]
            diff = _diff(time, usno_time)
            
            if abs(diff) >= _BIG_DIFF:
                _big_diffs[diff].append(
                    (table.type, table.lat, table.lon, time, usno_time))
                diff_counts[_sign(diff) * _BIG_DIFF] += 1
                
            else:
                diff_counts[diff] += 1
                
            del unmatched_usno_times[i]
            
        else:
            # no time in `unmatched_usno_times` was close to `time`
            
            unmatched_times.append(time)
            
    diff_counts = _get_diff_counts_tuple(diff_counts)
    unmatched_time_counts = (len(unmatched_times), len(unmatched_usno_times))
    
    return diff_counts + unmatched_time_counts
    
    
def _find_time(time, times):
    
    i = bisect.bisect_left(times, time)
    
    if i != len(times) and _is_close(time, times[i]):
        return i
    elif i != 0 and _is_close(time, times[i - 1]):
        return i - 1
    else:
        return -1
        
        
def _is_close(t0, t1):
    return abs(_diff(t0, t1)) < _DISTINCT_EVENTS_DIFF


def _diff(t0, t1):
    return int(round((t0 - t1).total_seconds() / 60.))


def _sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
    
    
def _get_diff_counts_tuple(diff_counts):
    indices = xrange(-_BIG_DIFF, _BIG_DIFF + 1)
    return tuple(diff_counts[indices])


def _format(d):
    if isinstance(d, six.string_types):
        return '"' + d + '"'
    else:
        return str(d)
    
    
def _write_big_diffs_file():
    
    big_diffs_file_path = os.path.join(_DATA_DIR_PATH, _BIG_DIFFS_FILE_NAME)
    
    with open(big_diffs_file_path, 'w') as file_:
        
        file_.write('All PyEphem/USNO differences larger than one minute:')
        
        diffs = _big_diffs.keys()
        diffs.sort()
        
        for diff in diffs:
            file_.write('\n' + str(diff) + '\n')
            for data in _big_diffs[diff]:
                file_.write('    ' + str(data) + '\n')


if __name__ == '__main__':
    _main()
