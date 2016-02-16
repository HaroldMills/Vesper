"""
Downloads rise/set tables from the United States Naval Observatory.
"""


from __future__ import print_function
import datetime
import math
import os
import random
import time

from vesper.util.usno_rise_set_table import UsnoRiseSetTable


_TABLES_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/USNO Tables Test'

_TABLE_TYPES = (
    'Sunrise/Sunset',
    'Moonrise/Moonset',
    'Civil Twilight',
    'Nautical Twilight',
    'Astronomical Twilight'
)

_GRID_LATS = range(-80, 81, 20)       # 9 latitudes
_GRID_LONS = range(-180, 151, 60)     # 6 longitudes
_GRID_YEARS = range(1990, 2031, 10)   # 5 years

_SPECIFIC_LOCATION_YEARS = range(1990, 2031, 1)
_SPECIFIC_LOCATIONS = (
    (42.45, -76.5, -4, 'Ithaca, NY'),
    (46.70, -114.0, -6, 'MPG Ranch')
)

_NUM_RANDOM_TABLES = 1000
_RANDOM_LAT_RANGE = (-80, 80)
_RANDOM_YEAR_RANGE = (1990, 2030)

_DRY_RUN = True

_START_TIME = datetime.datetime(2015, 6, 21)

_PAUSE_DURATION = 15
"""Duration of pause that precedes each file download, in seconds."""

_FILE_NAME_TABLE_TYPES = {
    'Sunrise/Sunset': 'Sunrise-Sunset',
    'Moonrise/Moonset': 'Moonrise-Moonset'
}

def _main():
    
    if not _DRY_RUN:
        _wait_until_time(_START_TIME)
        
    # _download_grid_tables()
    # _download_specific_location_tables()
    _download_random_tables()
    
    
def _wait_until_time(dt):
    while datetime.datetime.now() < dt:
        time.sleep(5)
        
    
def _download_grid_tables():
    for data in _generateGridTableData():
        _download_table(*data)
        
        
def _generateGridTableData():
    for table_type in _TABLE_TYPES:
        for lat in _GRID_LATS:
            for lon in _GRID_LONS:
                for year in _GRID_YEARS:
                    yield (table_type, lat, lon, year)


def _download_specific_location_tables():
    for table_type, lat, lon, year, utc_offset, place_name in \
            _generateSpecificLocationsTableData():
        _download_table(table_type, lat, lon, year, utc_offset, place_name)
        
        
def _generateSpecificLocationsTableData():
    for table_type in _TABLE_TYPES:
        for lat, lon, utc_offset, place_name in _SPECIFIC_LOCATIONS:
            for year in _SPECIFIC_LOCATION_YEARS:
                yield (table_type, lat, lon, year, utc_offset, place_name)
            

def _download_random_tables():
    for data in _generateRandomTableData():
        _download_table(*data)
        
        
def _generateRandomTableData():
    
    # Seed the random number generator so we will get the same sequence
    # of (pseudo-) random numbers in different runs of this script.
    random.seed(0)
    
    for _ in xrange(_NUM_RANDOM_TABLES):
        
        table_type = random.choice(_TABLE_TYPES)
        lat = _generateRandomLatitude()
        lon = random.uniform(-180, 180)
        year = random.randint(*_RANDOM_YEAR_RANGE)
        
        yield (table_type, lat, lon, year)
    
    
def _generateRandomLatitude():
    # TODO: There's a better way to do this that generates only a single
    # random number, transforming it according to the desired PDF. Figure
    # out the algorithm and implement it.
    while True:
        lat = random.uniform(*_RANDOM_LAT_RANGE)
        x = random.uniform(0, 1)
        if x <= math.cos(math.radians(lat)):
            return lat
        
        
def _download_table(
        table_type, lat, lon, year, utc_offset=None, place_name=None):
    
    if _DRY_RUN:
        table = str(datetime.datetime.now()) + '\n'
        
    else:
        # not a dry run
        
        # Be polite by pausing before each download.
        time.sleep(_PAUSE_DURATION)
        
        table = UsnoRiseSetTable.download_table_text(
            table_type, lat, lon, year, utc_offset, place_name)
    
    file_name = _create_table_file_name(table_type, lat, lon, year)
    file_path = os.path.join(_TABLES_DIR_PATH, file_name)
    print('writing file "{}"...'.format(file_name))
    _write_file(file_path, table)
    
    
def _create_table_file_name(table_type, lat, lon, year):
    table_type = _FILE_NAME_TABLE_TYPES.get(table_type, table_type)
    lat = _format_angle(lat, '{:05.2f}')
    lon = _format_angle(lon, '{:05.1f}')
    return '{}_{}_{}_{}.txt'.format(table_type, lat, lon, year)


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
