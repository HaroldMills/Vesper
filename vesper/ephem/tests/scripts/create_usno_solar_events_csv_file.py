"""
Script that creates solar event CSV files from a collection of USNO tables.

The script assumes that every .txt file in the input directory (including
its subdirectories) is a USNO rise/set table. It creates one output CSV
file named "USNO Solar Events.csv".
"""


from pathlib import Path
import csv
import datetime

from vesper.ephem.usno_rise_set_table import UsnoRiseSetTable


DATA_DIR_PATH = Path('/Users/harold/Desktop/NFC/Data/Astronomy/USNO Tables')

OUTPUT_FILE_PATH = DATA_DIR_PATH / 'USNO Solar Events.csv'

OUTPUT_COLUMN_NAMES = (
    'Latitude',
    'Longitude',
    'Time',
    'Local Day',
    'Local Night',
    'Event')

RISING_EVENT_NAMES = {
    'Astronomical Twilight': 'Astronomical Dawn',
    'Nautical Twilight': 'Nautical Dawn',
    'Civil Twilight': 'Civil Dawn',
    'Sunrise/Sunset': 'Sunrise'
}

SETTING_EVENT_NAMES = {
    'Sunrise/Sunset': 'Sunset',
    'Civil Twilight': 'Civil Dusk',
    'Nautical Twilight': 'Nautical Dusk',
    'Astronomical Twilight': 'Astronomical Dusk'
}

ONE_DAY = datetime.timedelta(days=1)


def main():
    
    with open(OUTPUT_FILE_PATH, 'w') as output_file:
        
        writer = csv.writer(output_file)
        
        writer.writerow(OUTPUT_COLUMN_NAMES)
        
        rows = get_csv_file_rows()
        
#         print(f'Table has {len(rows)} rows.')
#         for row in rows[:10]:
#             print(row)
#             
        writer.writerows(rows)
        
        
def get_csv_file_rows():
    
    rows = []
    
    for file_path in DATA_DIR_PATH.glob('**/*.txt'):
        
        if file_path.parent.name != 'Moon':
            
            with open(file_path) as table_file:
                table_text = table_file.read()
                
            t = UsnoRiseSetTable(table_text)
            
            if (table_included(t)):
                
                print(
                    t.lat, t.lon, t.year, t.type, t.utc_offset,
                    len(t.rising_times), len(t.setting_times))
            
                time_zone = datetime.timezone(t.utc_offset)
                
                event_name = RISING_EVENT_NAMES[t.type]
                add_event_rows(
                    t.lat, t.lon, t.rising_times, time_zone, event_name, rows)
                
                event_name = SETTING_EVENT_NAMES[t.type]
                add_event_rows(
                    t.lat, t.lon, t.setting_times, time_zone, event_name, rows)
            
    rows.sort()
    
    return rows


def table_included(table):
    lon = table.lon
    year = table.year
    return lon == -76.5 or lon == -114 or (lon % 60 == 0 and year % 10 == 0)


def add_event_rows(lat, lon, event_times, time_zone, event_name, rows):
    
    for utc_dt in event_times:
        
        # Get event day.
        local_dt = utc_dt.astimezone(time_zone)
        local_day = local_dt.date()
        
        # Get event night.
        if local_dt.hour < 12:
            local_night = local_day - ONE_DAY
        else:
            local_night = local_day
        
        row = (
            lat, lon,
            str(utc_dt), str(local_day), str(local_night),
            event_name)
        
        rows.append(row)
        

if __name__ == '__main__':
    main()
