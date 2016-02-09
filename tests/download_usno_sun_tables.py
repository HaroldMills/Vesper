"""
Downloads sunrise/sunset tables from the United States Naval Observatory.
"""


from __future__ import print_function
import datetime
import os
import time

from vesper.util.usno_sun_moon_table import UsnoSunMoonTable


_DRY_RUN = True

_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/USNO Tables Test'

_GRID_LATS = range(-80, 81, 20)       # 9 latitudes
_GRID_LONS = range(-180, 151, 60)     # 6 longitudes
_GRID_YEARS = range(1990, 2031, 10)   # 5 years

_EXTRA_LOCATION_YEARS = range(1990, 2031, 1)
_EXTRA_LOCATIONS = (
    (42.45, -76.5, -4, 'Ithaca, NY'),
    (46.70, -114.0, -6, 'MPG Ranch')
)

_TABLE_TYPES = (
    'Moon', 'Civil Twilight', 'Nautical Twilight', 'Astronomical Twilight')

_START_TIME = datetime.datetime(2015, 6, 21)

_PAUSE_DURATION = 15 if not _DRY_RUN else 0
'''Duration of pause that precedes each file download, in seconds.'''

_TABLE_TYPES_DICT = {
    'Sun': 'Sunrise/Sunset',
    'Moon': 'Moonrise/Moonset'
}


def _main():
    
    _wait_until_time(_START_TIME)
    
    for table_type in _TABLE_TYPES:
        
        for lat in _GRID_LATS:
            for lon in _GRID_LONS:
                for year in _GRID_YEARS:
                    _download_table('Grid', table_type, lat, lon, year)

        for lat, lon, utc_offset, place_name in _EXTRA_LOCATIONS:
            for year in _EXTRA_LOCATION_YEARS:
                _download_table(
                    place_name, table_type, lat, lon, year, utc_offset,
                    place_name)
            

def _wait_until_time(dt):
    while datetime.datetime.now() < dt:
        time.sleep(5)
        
    
def _download_table(
        subdir_name, table_type, lat, lon, year, utc_offset=None,
        place_name=None):
    
    _pause(_PAUSE_DURATION)
    
    if _DRY_RUN:
        table = str(datetime.datetime.now()) + '\n'
    else:
        type_ = _TABLE_TYPES_DICT.get(table_type, table_type)
        table = UsnoSunMoonTable.download_table_text(
            type_, lat, lon, year, utc_offset, place_name)
    
    file_name = _create_table_file_name(table_type, lat, lon, year, place_name)
    file_path = os.path.join(_DIR_PATH, subdir_name, table_type, file_name)
    print('writing file "{:s}"...'.format(file_name))
    _write_file(file_path, table)
    
    
def _pause(duration):
    if duration != 0:
        time.sleep(duration)
    
    
def _create_table_file_name(table_type, lat, lon, year, name=None):
    lat = _format_angle(lat, '{:05.2f}')
    lon = _format_angle(lon, '{:05.1f}')
    prefix = '{:s}_{:s}_{:s}_{:d}'.format(table_type, lat, lon, year)
    name = ('_' + name) if name is not None else ''
    return prefix + name + '.txt'


def _format_angle(x, format_):
    if x < 0:
        return '-' + format_.format(-x)
    else:
        return format_.format(x)
    
    
def _write_file(file_path, contents):
    
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        
    with open(file_path, 'w') as file_:
        file_.write(contents)
        
        
if __name__ == '__main__':
    _main()
