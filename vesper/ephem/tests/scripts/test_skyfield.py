"""
Script that tests the Skyfield Python package by comparing its output
to tables produced by the U.S. Naval Observatory (USNO).
"""


from collections import defaultdict
from pathlib import Path
import csv
import datetime

from vesper.ephem.astronomical_calculator import AstronomicalCalculator
from vesper.ephem.usno_rise_set_table import UsnoRiseSetTable


DATA_DIR_PATH = Path('/Users/harold/Desktop/NFC/Data/Astronomy')

USNO_TABLES_DIR_PATH = DATA_DIR_PATH / 'USNO Tables'

RESULTS_DIR_PATH = DATA_DIR_PATH / 'Skyfield Test Results'

DIFF_COUNT_FILE_PATH = \
    RESULTS_DIR_PATH / 'Twilight Event Difference Counts.csv'

UNMATCHED_EVENTS_FILE_PATH = RESULTS_DIR_PATH / 'Unmatched Twilight Events.csv'

SOLAR_TABLE_TYPES = frozenset((
    'Astronomical Twilight',
    'Nautical Twilight',
    'Civil Twilight',
    'Sunrise/Sunset'
))

RISING_EVENT_NAMES = {
    'Astronomical Twilight': 'Astronomical Dawn',
    'Nautical Twilight': 'Nautical Dawn',
    'Civil Twilight': 'Civil Dawn',
    'Sunrise/Sunset': 'Sunrise'
}

SETTING_EVENT_NAMES = {
    'Astronomical Twilight': 'Astronomical Dusk',
    'Nautical Twilight': 'Nautical Dusk',
    'Civil Twilight': 'Civil Dusk',
    'Sunrise/Sunset': 'Sunset'
}

EVENT_NAMES = (
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise',
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk'
)

DIFF_COUNT_FILE_COLUMN_NAMES = (
    'Latitude',
    'Longitude',
    'Year',
    'Event Name',
    '-2 Diffs',
    '-1 Diffs',
    '0 Diffs',
    '1 Diffs',
    '2 Diffs',
    'Unmatched Skyfield Events',
    'Unmatched USNO Events'
)

UNMATCHED_EVENT_FILE_COLUMN_NAMES = (
    'Latitude',
    'Longitude',
    'Year',
    'Time',
    'Event Name',
    'Source'
)


def create_count_dict():
    return defaultdict(int)


skyfield_event_cache = {}
"""(lat, lon, year) -> (time, event_name) list"""

event_time_diff_counts = defaultdict(create_count_dict)
"""(lat, lon, year, event name) -> diff -> count"""

unmatched_event_counts = defaultdict(create_count_dict)
"""source name -> (lat, lon, year, event name) -> count"""

unmatched_events = []
"""(source, (lat, lon, year, event name), time) list"""


def main():
    
    table_file_paths = sorted(USNO_TABLES_DIR_PATH.glob('**/*.txt'))
    
    # table_file_paths = table_file_paths[:2]
    
    table_file_count = len(table_file_paths)
    
    for i, table_file_path in enumerate(table_file_paths):
    
        print(
            f'Processing USNO table "{table_file_path.name}" '
            f'(file {i + 1} of {table_file_count})...')
        
        t = read_usno_table(table_file_path)
        
        # if t.lat != -80 or t.lon != -180:
        #     continue
        
        if t.type in SOLAR_TABLE_TYPES:
            
            usno_times = t.rising_times
            event_name = RISING_EVENT_NAMES[t.type]
            get_and_match_skyfield_events(t, usno_times, event_name)
            
            usno_times = t.setting_times
            event_name = SETTING_EVENT_NAMES[t.type]
            get_and_match_skyfield_events(t, usno_times, event_name)
            
    write_diff_count_file(DIFF_COUNT_FILE_PATH)
    write_unmatched_events_file(UNMATCHED_EVENTS_FILE_PATH)


def read_usno_table(file_path):
    
    with open(file_path) as table_file:
        text = table_file.read()
        
    return UsnoRiseSetTable(text)


def get_and_match_skyfield_events(t, usno_times, event_name):
    
    sf_times = get_skyfield_event_times(
        t.lat, t.lon, t.year, event_name, t.utc_offset)
    
    match_events(t.lat, t.lon, t.year, event_name, sf_times, usno_times)


def get_skyfield_event_times(lat, lon, year, event_name, utc_offset):
    
    events = skyfield_event_cache.get((lat, lon, year))
    
    if events is None:
        
        # Get all Skyfield events for the specified lat, lon, and year.
        time_zone = datetime.timezone(utc_offset)
        c = AstronomicalCalculator(lat, lon, time_zone)
        start_time = datetime.datetime(year, 1, 1, tzinfo=time_zone)
        end_time = datetime.datetime(year + 1, 1, 1, tzinfo=time_zone)
        events = c.get_twilight_events(start_time, end_time)
        
        skyfield_event_cache[(lat, lon, year)] = events
    
    # Get times of events of interest.
    times = [time for time, name in events if name == event_name]
    
    return times


def match_events(lat, lon, year, event_name, sf_times, usno_times):
    
    key = (lat, lon, year, event_name)
    
    sf_count = len(sf_times)
    usno_count = len(usno_times)
    
    sf_index = 0
    usno_index = 0
    
    while sf_index != sf_count and usno_index != usno_count:
        
        sf_time = sf_times[sf_index]
        usno_time = usno_times[usno_index]
        
        diff = int(round((sf_time - usno_time).total_seconds() / 60))
        
        if abs(diff) <= 2:
            # times close: events match
            
            event_time_diff_counts[key][diff] += 1
            sf_index += 1
            usno_index += 1
        
        else:
            # times not close: events do not match
            
            if diff < 0:
                # Skyfield time precedes USNO time
                
                record_unmatched_event('Skyfield', key, sf_time)
                sf_index += 1
                
            else:
                # USNO time precedes Skyfield time
                
                record_unmatched_event('USNO', key, usno_time)
                usno_index += 1
            
    while sf_index != sf_count:
        sf_time = sf_times[sf_index]
        record_unmatched_event('Skyfield', key, sf_time)
        sf_index += 1
        
    while usno_index != usno_count:
        usno_time = usno_times[usno_index]
        record_unmatched_event('USNO', key, usno_time)
        usno_index += 1


def record_unmatched_event(source, key, time):
    unmatched_event_counts[source][key] += 1
    unmatched_events.append((source, key, time))


def write_diff_count_file(file_path):
    
    with open(file_path, 'w') as csv_file:
        
        writer = csv.writer(csv_file)
        
        writer.writerow(DIFF_COUNT_FILE_COLUMN_NAMES)
        
        keys = sorted(event_time_diff_counts.keys())
        
        for key in keys:
            
            c = event_time_diff_counts[key]
            sf = unmatched_event_counts['Skyfield'][key]
            usno = unmatched_event_counts['USNO'][key]
            
            lat, lon, year, event_name = key
            
            writer.writerow((
                lat, lon, year, event_name,
                c[-2], c[-1], c[0], c[1], c[2],
                sf, usno))
            
            
def write_unmatched_events_file(file_path):
    
    with open(file_path, 'w') as csv_file:
        
        writer = csv.writer(csv_file)
        
        writer.writerow(UNMATCHED_EVENT_FILE_COLUMN_NAMES)
        
        rows = [get_unmatched_events_file_row(*e) for e in unmatched_events]
        rows.sort()
        
        writer.writerows(rows)
           
    
def get_unmatched_events_file_row(source, key, time):
    lat, lon, year, event_name = key
    return lat, lon, year, str(time), event_name, source


if __name__ == '__main__':
    main()
