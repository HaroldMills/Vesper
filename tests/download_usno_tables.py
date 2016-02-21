"""
Downloads rise/set tables from the United States Naval Observatory.
"""


from __future__ import print_function
import datetime
import math
import os
import random
import time as time_module

from vesper.util.usno_altitude_azimuth_table import UsnoAltitudeAzimuthTable
from vesper.util.usno_rise_set_table import UsnoRiseSetTable


_TABLES_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\USNO Tables Test'

_YEAR_TABLE_TYPES = (
    'Sunrise/Sunset',
    'Moonrise/Moonset',
    'Civil Twilight',
    'Nautical Twilight',
    'Astronomical Twilight'
)

_DAY_TABLE_TYPES = (
    'Sun Altitude/Azimuth',
    'Moon Altitude/Azimuth'
)

_YEAR_RANGE = (1990, 2030)
_DAY_TABLE_INTERVAL = 10

_SPECIFIC_LOCATIONS = (
    (42.45, -76.5, -4, 'Ithaca, NY'),
    (46.70, -114.0, -6, 'MPG Ranch')
)
_NUM_SPECIFIC_LOCATION_DATES = 300

_NUM_RANDOM_YEAR_TABLES = 10 # 1000
_NUM_RANDOM_DAY_TABLES = 10 # 1000
_RANDOM_LAT_RANGE = (-80, 80)

_DRY_RUN = False

_START_TIME = datetime.datetime(2016, 2, 20, 19, 42)

_PAUSE_DURATION = 10
"""Duration of pause that precedes each file download, in seconds."""

_RISE_SET = UsnoRiseSetTable.download_table_text
_ALTITUDE_AZIMUTH = UsnoAltitudeAzimuthTable.download_table_text
_DOWNLOAD_FUNCTIONS = {
    'Sunrise/Sunset': _RISE_SET,
    'Moonrise/Moonset': _RISE_SET,
    'Civil Twilight': _RISE_SET,
    'Nautical Twilight': _RISE_SET,
    'Astronomical Twilight': _RISE_SET,
    'Sun Altitude/Azimuth': _ALTITUDE_AZIMUTH,
    'Moon Altitude/Azimuth': _ALTITUDE_AZIMUTH
}

_FILE_NAME_TABLE_TYPES = {
    'Sunrise/Sunset': 'Sunrise Sunset',
    'Moonrise/Moonset': 'Moonrise Moonset',
    'Sun Altitude/Azimuth': 'Sun Altitude Azimuth',
    'Moon Altitude/Azimuth': 'Moon Altitude Azimuth'
}


def _main():
    
    if not _DRY_RUN:
        _wait_until_time(_START_TIME)
        
    # _download_specific_location_tables()
    _download_random_tables()
    
    
def _wait_until_time(dt):
    while datetime.datetime.now() < dt:
        time_module.sleep(5)
        
    
def _download_specific_location_tables():
    for data in _generate_specific_locations_year_table_data():
        _download_table(*data)
    for data in _generate_specific_locations_day_table_data():
        _download_table(*data)
        
        
def _generate_specific_locations_year_table_data():
    start_year, end_year = _YEAR_RANGE
    years = range(start_year, end_year + 1)
    for table_type in _YEAR_TABLE_TYPES:
        for lat, lon, utc_offset, place_name in _SPECIFIC_LOCATIONS:
            for year in years:
                yield (table_type, lat, lon, year, utc_offset, place_name)
            

def _generate_specific_locations_day_table_data():
    _seed_random_number_generator()
    for date in _get_random_dates(_NUM_SPECIFIC_LOCATION_DATES, *_YEAR_RANGE):
        for table_type in _DAY_TABLE_TYPES:
            for lat, lon, utc_offset, place_name in _SPECIFIC_LOCATIONS:
                yield (table_type, lat, lon, date, _DAY_TABLE_INTERVAL,
                       utc_offset, place_name)
        
        
def _seed_random_number_generator():
    # Seed the random number generator so we will get the same sequence
    # of pseudorandom numbers in different runs of this script.
    random.seed(0)
    
    
def _get_random_dates(num_dates, start_year, end_year):
    start_date = datetime.date(start_year, 1, 1)
    num_days = _get_num_days_in_year_range(start_year, end_year)
    if num_days < num_dates:
        num_dates = num_days
    day_nums = random.sample(xrange(0, num_days), num_dates)
    dates = [start_date + datetime.timedelta(days=n) for n in day_nums]
    return dates


def _get_num_days_in_year_range(start_year, end_year):
    start_date = datetime.date(start_year, 1, 1)
    end_date = datetime.date(end_year + 1, 1, 1)
    num_days = (end_date - start_date).days
    return num_days


def _download_random_tables():
    for data in _generate_random_year_table_data():
        _download_table(*data)
    for data in _generate_random_day_table_data():
        _download_table(*data)
        
        
def _generate_random_year_table_data():
    _seed_random_number_generator()
    for _ in xrange(_NUM_RANDOM_YEAR_TABLES):
        table_type = random.choice(_YEAR_TABLE_TYPES)
        lat = _get_random_latitude()
        lon = _get_random_longitude()
        year = random.randint(*_YEAR_RANGE)
        yield (table_type, lat, lon, year)
    
    
def _get_random_latitude():
    # TODO: There's a better way to do this that generates only a single
    # random number, transforming it according to the desired PDF. Figure
    # out the algorithm and implement it.
    while True:
        lat = random.uniform(*_RANDOM_LAT_RANGE)
        x = random.uniform(0, 1)
        if x <= math.cos(math.radians(lat)):
            return lat
        
        
def _get_random_longitude():
    return random.uniform(-180, 180)


def _generate_random_day_table_data():
    _seed_random_number_generator()
    for _ in xrange(_NUM_RANDOM_DAY_TABLES):
        table_type = random.choice(_DAY_TABLE_TYPES)
        lat = _get_random_latitude()
        lon = _get_random_longitude()
        date = _get_random_date(*_YEAR_RANGE)
        yield (table_type, lat, lon, date, _DAY_TABLE_INTERVAL)
        
        
def _get_random_date(start_year, end_year):
    start_date = datetime.date(start_year, 1, 1)
    num_days = _get_num_days_in_year_range(start_year, end_year)
    day_num = random.randint(0, num_days - 1)
    date = start_date + datetime.timedelta(days=day_num)
    return date


def _download_table(table_type, lat, lon, time, *args):
    
    # Be polite by pausing before each download.
    time_module.sleep(_PAUSE_DURATION)
        
    if _DRY_RUN:
        table = str(datetime.datetime.now()) + '\n'
        
    else:
        # not a dry run
        
        function = _DOWNLOAD_FUNCTIONS[table_type]
        table = function(table_type, lat, lon, time, *args)
    
    file_name = _create_table_file_name(table_type, lat, lon, time)
    file_path = os.path.join(_TABLES_DIR_PATH, file_name)
    print('writing file "{}"...'.format(file_name))
    _write_file(file_path, table)
    
    
def _create_table_file_name(table_type, lat, lon, time):
    
    table_type = _FILE_NAME_TABLE_TYPES.get(table_type, table_type)
    lat = _format_angle(lat, '{:05.2f}')
    lon = _format_angle(lon, '{:05.1f}')
    
    # If `time` is a `datetime.date`, we format it. Otherwise we assume
    # it is a four-digit integer year that will format just fine with
    # the default integer formatter.
    if isinstance(time, datetime.date):
        time = time.strftime('%Y-%m-%d')
        
    return '{}_{}_{}_{}.txt'.format(table_type, lat, lon, time)


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
