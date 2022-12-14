"""
Script that creates CSV files from a directory of USNO tables.

The script assumes that every file in the input directory is either a
rise/set table or an altitude/azimuth table. It creates two CSV files,
one named "USNO Rise Set Data.csv" and the other named
"USNO Altitude Azimuth Data.csv".
"""


import csv
import datetime
import os

import vesper.ephem.usno_table_utils as utils


_DATA_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data'
_TABLES_DIR_PATH = os.path.join(_DATA_DIR_PATH, 'USNO Tables Test')
_RS_CSV_FILE_PATH = os.path.join(_DATA_DIR_PATH, 'USNO Rise Set Data.csv')
_AA_CSV_FILE_PATH = os.path.join(
    _DATA_DIR_PATH, 'USNO Altitude Azimuth Data.csv')
_RS_COLUMN_NAMES = (
    'Latitude', 'Longitude', 'Local Date', 'Event', 'UTC Time')
_AA_COLUMN_NAMES = (
    'Latitude', 'Longitude', 'UTC Time', 'Body', 'Altitude', 'Azimuth',
    'Illumination')
_RS_TABLE_TYPES = frozenset(utils.RISE_SET_TABLE_TYPES)
_AA_TABLE_TYPES = frozenset(utils.ALTITUDE_AZIMUTH_TABLE_TYPES)


def _main():
    
    rs_file, rs_writer = _open_csv_file(_RS_CSV_FILE_PATH, _RS_COLUMN_NAMES)
    aa_file, aa_writer = _open_csv_file(_AA_CSV_FILE_PATH, _AA_COLUMN_NAMES)
    
    for (dir_path, _, file_names) in os.walk(_TABLES_DIR_PATH):
        
        for file_name in file_names:
            
            table = _create_table(dir_path, file_name)
            
            if table.type in _RS_TABLE_TYPES:
                _append_rs_table_data(table, rs_writer)
            else:
                _append_aa_table_data(table, aa_writer)
                
            print(file_name, table.type)
            
    rs_file.close()
    aa_file.close()

    
def _open_csv_file(file_path, column_names):
    file_ = open(file_path, 'w', newline='')
    writer = csv.writer(file_)
    writer.writerow(column_names)
    return (file_, writer)
    

def _create_table(dir_path, file_name):
    
    file_name_table_type = file_name.split('_')[0]
    table_type = utils.get_table_type(file_name_table_type)
    table_class = utils.get_table_class(table_type)
    
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'r') as file_:
        table_text = file_.read()
    return table_class(table_text)


_RISE_EVENTS = {
    'Sunrise/Sunset': 'Sunrise',
    'Moonrise/Moonset': 'Moonrise',
    'Civil Twilight': 'Civil Dawn',
    'Nautical Twilight': 'Nautical Dawn',
    'Astronomical Twilight': 'Astronomical Dawn'
}


_SET_EVENTS = {
    'Sunrise/Sunset': 'Sunset',
    'Moonrise/Moonset': 'Moonset',
    'Civil Twilight': 'Civil Dusk',
    'Nautical Twilight': 'Nautical Dusk',
    'Astronomical Twilight': 'Astronomical Dusk'
}


def _append_rs_table_data(table, writer):
    
    rows = []
    
    lat = table.lat
    lon = table.lon
    
    event = _RISE_EVENTS[table.type]
    _append_rows(rows, lat, lon, event, table.rising_times)
    
    event = _SET_EVENTS[table.type]
    _append_rows(rows, lat, lon, event, table.setting_times)
    
    writer.writerows(rows)
    
    
def _append_rows(rows, lat, lon, event, times):
    for dt in times:
        local_dt = _get_naive_local_time(dt, lon)
        date = local_dt.date()
        time = dt.strftime('%Y-%m-%d %H:%M')
        rows.append((lat, lon, date, event, time))
        

def _get_naive_local_time(time, lon):
    naive_time = time.replace(tzinfo=None)
    utc_offset = datetime.timedelta(hours=lon * 24. / 360.)
    return naive_time + utc_offset


def _append_aa_table_data(table, writer):
    
    rows = []
    
    lat = table.lat
    lon = table.lon
    body = table.body
    
    for data in table.data:
        
        if table.body == 'Sun':
            (time, alt, az) = data
            illumination = None
        else:
            (time, alt, az, illumination) = data
            
        time = time.strftime('%Y-%m-%d %H:%M')
        
        rows.append((lat, lon, time, body, alt, az, illumination))
            
    writer.writerows(rows)


if __name__ == '__main__':
    _main()
    