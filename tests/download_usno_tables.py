"""
Downloads rise/set tables from the United States Naval Observatory.
"""


import argparse
import datetime
import math
import os
import random
import time as time_module

import vesper.util.usno_table_utils as utils


_TABLES_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\USNO Tables Test'

_YEAR_RANGE = (1990, 2030)
_AA_TABLE_INTERVAL = 10

_SPECIFIC_LOCATIONS = (
    (42.45, -76.5, -4, 'Ithaca, NY'),
    (46.70, -114.0, -6, 'MPG Ranch')
)
_NUM_SPECIFIC_LOCATION_DATES = 300

_NUM_RANDOM_RS_TABLES = 10 # 1000
_NUM_RANDOM_AA_TABLES = 10 # 1000
_RANDOM_LAT_RANGE = (-80, 80)

_DRY_RUN = True

_START_TIME = datetime.datetime(2016, 2, 20, 19, 42)

_PAUSE_DURATION = 10
"""Duration of pause that precedes each file download, in seconds."""


def _main():
    
    args = _parse_args()
    
    if not _DRY_RUN:
        _wait_until_time(_START_TIME)
        
    # _download_specific_location_tables()
    _download_random_tables()
    
    
def _parse_args():
    
    parser = argparse.ArgumentParser(
        description='''
            This script downloads rise/set and altitude/azimuth tables
            from the United States Naval Observatory (USNO).''')
    
    date_format = 'YYYY-MM-DD'
    
    parser.add_argument(
        '--tables-dir_path', default=None,
        help='the directory to which to download tables.')
    
    parser.add_argument(
        '--dry-run', action='store_true', default=False,
        help=(
            'run but do not actually download tables. Write table '
            'files but store the date and time of writing in each '
            'file rather than a USNO table.'))
    
    parser.add_argument(
        '--start-time', default=None, metavar='YYYY-MM-DD HH:MM',
        help=(
            'the time at which to begin downloading tables. If no '
            'time is specified, downloading begins immediately.'))
    
    parser.add_argument(
        '--pause-duration', type=int, default=None,
        help=(
            'the duration in seconds of the pause between consecutive '
            'table downloads'))
    
    args = parser.parse_args()
    
    return args


def _wait_until_time(dt):
    while datetime.datetime.now() < dt:
        time_module.sleep(5)
        
    
def _download_specific_location_tables():
    for data in _generate_specific_locations_rs_table_data():
        _download_table(*data)
    for data in _generate_specific_locations_aa_table_data():
        _download_table(*data)
        
        
def _generate_specific_locations_rs_table_data():
    start_year, end_year = _YEAR_RANGE
    years = range(start_year, end_year + 1)
    for table_type in utils.RISE_SET_TABLE_TYPES:
        for lat, lon, utc_offset, place_name in _SPECIFIC_LOCATIONS:
            for year in years:
                yield (table_type, lat, lon, year, utc_offset, place_name)
            

def _generate_specific_locations_aa_table_data():
    _seed_random_number_generator()
    for date in _get_random_dates(_NUM_SPECIFIC_LOCATION_DATES, *_YEAR_RANGE):
        for table_type in utils.ALTITUDE_AZIMUTH_TABLE_TYPES:
            for lat, lon, utc_offset, place_name in _SPECIFIC_LOCATIONS:
                yield (table_type, lat, lon, date, _AA_TABLE_INTERVAL,
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
    day_nums = random.sample(range(0, num_days), num_dates)
    dates = [start_date + datetime.timedelta(days=n) for n in day_nums]
    return dates


def _get_num_days_in_year_range(start_year, end_year):
    start_date = datetime.date(start_year, 1, 1)
    end_date = datetime.date(end_year + 1, 1, 1)
    num_days = (end_date - start_date).days
    return num_days


def _download_random_tables():
    for data in _generate_random_rs_table_data():
        _download_table(*data)
    for data in _generate_random_aa_table_data():
        _download_table(*data)
        
        
def _generate_random_rs_table_data():
    _seed_random_number_generator()
    for _ in range(_NUM_RANDOM_RS_TABLES):
        table_type = random.choice(utils.RISE_SET_TABLE_TYPES)
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


def _generate_random_aa_table_data():
    _seed_random_number_generator()
    for _ in range(_NUM_RANDOM_AA_TABLES):
        table_type = random.choice(utils.ALTITUDE_AZIMUTH_TABLE_TYPES)
        lat = _get_random_latitude()
        lon = _get_random_longitude()
        date = _get_random_date(*_YEAR_RANGE)
        yield (table_type, lat, lon, date, _AA_TABLE_INTERVAL)
        
        
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
        table = utils.download_table(table_type, lat, lon, time, *args)
    
    file_name = _create_table_file_name(table_type, lat, lon, time)
    file_path = os.path.join(_TABLES_DIR_PATH, file_name)
    print('writing file "{}"...'.format(file_name))
    _write_file(file_path, table)
    
    
def _create_table_file_name(table_type, lat, lon, time):
    
    table_type = utils.get_file_name_table_type(table_type)
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
