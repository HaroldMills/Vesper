from collections import defaultdict
from pathlib import Path
import csv
import datetime

from vesper.ephem.astronomical_calculator import AstronomicalCalculator
from vesper.ephem.usno_rise_set_table import UsnoRiseSetTable


USNO_TABLES_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Astronomy/USNO Tables')

OUTPUT_FILE_PATH = USNO_TABLES_DIR_PATH / 'Solar Event Differences.csv'

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

OUTPUT_COLUMN_NAMES = (
    'Latitude',
    'Longitude',
    'Event Name',
    'Diff -2',
    'Diff -1',
    'Diff 0',
    'Diff 1',
    'Diff 2',
    'Unmatched Skyfield Events',
    'Unmatched USNO Events'
)


def create_count_dict():
    # event name -> count
    return defaultdict(int)


def create_diff_count_dict():
    # event name -> diff -> count
    return defaultdict(create_count_dict)


skyfield_event_cache = {}
"""(lat, lon, year) -> (time, event_name) list"""

unmatched_usno_event_counts = defaultdict(create_count_dict)
"""(lat, lon) -> event name -> count"""

unmatched_sf_event_counts = defaultdict(create_count_dict)
"""(lat, lon) -> event name -> count"""

event_time_diff_counts = defaultdict(create_diff_count_dict)
"""(lat, lon) -> event name -> diff -> count"""


def main():
    
    table_file_paths = list(USNO_TABLES_DIR_PATH.glob('**/*.txt'))
    
    table_file_paths = table_file_paths[:10]
    
    table_file_count = len(table_file_paths)
    
    for i, table_file_path in enumerate(table_file_paths):
    
        print(
            f'Processing table file "{table_file_path.name}" '
            f'(file {i + 1} of {table_file_count})...')
        
        t = read_usno_table(table_file_path)
        
        if t.type in SOLAR_TABLE_TYPES:
            
            usno_times = t.rising_times
            event_name = RISING_EVENT_NAMES[t.type]
            get_and_compare_skyfield_event_times(t, usno_times, event_name)
            
            usno_times = t.setting_times
            event_name = SETTING_EVENT_NAMES[t.type]
            get_and_compare_skyfield_event_times(t, usno_times, event_name)
            
    show_event_diffs()
    
    write_output_file(OUTPUT_FILE_PATH)
    
    
def get_and_compare_skyfield_event_times(t, usno_times, event_name):
    
    sf_times = get_skyfield_event_times(
        t.lat, t.lon, t.year, event_name, t.utc_offset)
    
    match_events(t.lat, t.lon, event_name, usno_times, sf_times)
    
    
def match_events(lat, lon, event_name, usno_times, sf_times):
    
    loc = (lat, lon)
    
    usno_count = len(usno_times)
    sf_count = len(sf_times)
    
    usno_index = 0
    sf_index = 0
    
    while usno_index != usno_count and sf_index != sf_count:
        
        usno_time = usno_times[usno_index]
        sf_time = sf_times[sf_index]
        
        diff = int(round((usno_time - sf_time).total_seconds() / 60))
        
        if abs(diff) <= 2:
            # times close: events match
            
            event_time_diff_counts[loc][event_name][diff] += 1
            usno_index += 1
            sf_index += 1
            
        else:
            # times not close: events do not match
            
            if diff < 0:
                # USNO time less than Skyfield time
                
                unmatched_usno_event_counts[loc][event_name] += 1
                usno_index += 1
                
            else:
                # Skyfield time less than or equal to USNO time
                
                unmatched_usno_event_counts[loc][event_name] += 1
                sf_index += 1
            
    unmatched_usno_event_counts[loc][event_name] += usno_count - usno_index
    unmatched_sf_event_counts[loc][event_name] += sf_count - sf_index


def get_skyfield_event_times(lat, lon, year, event_name, utc_offset):
    
    events = skyfield_event_cache.get((lat, lon, year))
    
    if events is None:
        
        # Get all Skyfield events for the specified lat, lon, and year.
        c = AstronomicalCalculator(lat, lon)
        time_zone = datetime.timezone(utc_offset)
        start_time = datetime.datetime(year, 1, 1, tzinfo=time_zone)
        end_time = datetime.datetime(year + 1, 1, 1, tzinfo=time_zone)
        events = c.get_solar_events(start_time, end_time)
        
        skyfield_event_cache[(lat, lon, year)] = events
    
    # Get times of events of interest.
    times = [time for time, name in events if name == event_name]
    
    return times
    
    
def read_usno_table(file_path):
    
    with open(file_path) as table_file:
        text = table_file.read()
        
    return UsnoRiseSetTable(text)


def show_event_diffs():
    show_unmatched_events(unmatched_sf_event_counts, 'Skyfield', 'USNO')
    show_unmatched_events(unmatched_usno_event_counts, 'USNO', 'Skyfield')
    show_event_time_diff_counts()
    show_aggregated_event_time_diff_counts()
    
    
def show_unmatched_events(events, name_a, name_b):
    
    locs = sorted(events.keys())
    
    for loc in locs:
        
        print(
            f'Location {loc} {name_a} events for which there was no '
            f'matching {name_b} event:')
        
        counts = events[loc]
        event_names = frozenset(counts.keys())
        
        for event_name in EVENT_NAMES:
            if event_name in event_names:
                count = counts[event_name]
                print(f'    {event_name}: {count}')
                
                
def show_event_time_diff_counts():
    
    diff_counts = event_time_diff_counts
    
    locs = sorted(diff_counts.keys())
    
    for loc in locs:
        
        print(f'Location {loc} event time differences:')
        
        count_dicts = diff_counts[loc]
        event_names = frozenset(count_dicts.keys())
        
        for event_name in EVENT_NAMES:
            if event_name in event_names:
                counts = count_dicts[event_name]
                show_diff_counts(event_name, counts)
    
    
def show_diff_counts(event_name, counts):
    counts_string = get_diff_counts_string(counts)
    normalized_counts_string = get_normalized_diff_counts_string(counts)
    print(f'    {event_name}: {counts_string} {normalized_counts_string}')


def get_diff_counts_string(counts):
    diffs = sorted(counts.keys())
    items = ', '.join([f'{diff}: {counts[diff]}' for diff in diffs])
    return '{' + items + '}'


def get_normalized_diff_counts_string(counts):
    
    # Get normalized counts.
    total = sum(counts.values())
    normalized_counts = dict(
        (diff, 100 * count / total) for diff, count in counts.items())
    
    # Format count items.
    diffs = sorted(counts.keys())
    items = ', '.join(
        [f'{diff}: {normalized_counts[diff]:.2f}' for diff in diffs])
    
    return '{' + items + '}'

    
def show_aggregated_event_time_diff_counts():
    
    # Have (lat, lon) -> event name -> diff -> count, want
    # event name -> diff -> count, i.e. counts aggregated over location.
    
    aggregated_counts = defaultdict(create_count_dict)
    
    diff_counts = event_time_diff_counts
    
    for _, count_dict in diff_counts.items():
        for event_name, counts in count_dict.items():
            for diff, count in counts.items():
                aggregated_counts[event_name][diff] += count
                
    print('Event time differences aggregated over location:')
    for event_name in EVENT_NAMES:
        counts = aggregated_counts[event_name]
        show_diff_counts(event_name, counts)
        
    print('Event time differences aggregated over location and event type:')
    total_counts = defaultdict(int)
    for counts in aggregated_counts.values():
        for diff, count in counts.items():
            total_counts[diff] += count
    show_diff_counts('All Events', total_counts)
            
            
def write_output_file(output_file_path):
    
    with open(output_file_path, 'w') as csv_file:
        
        writer = csv.writer(csv_file)
        
        writer.writerow(OUTPUT_COLUMN_NAMES)
        
        locs = sorted(event_time_diff_counts.keys())
        
        for loc in locs:
            
            lat, lon = loc
            
            for event_name in EVENT_NAMES:
                
                c = event_time_diff_counts[loc][event_name]
                sf = unmatched_sf_event_counts[loc][event_name]
                usno = unmatched_usno_event_counts[loc][event_name]
                
                writer.writerow((
                    lat, lon, event_name,
                    c[-2], c[-1], c[0], c[1], c[2],
                    sf, usno))


if __name__ == '__main__':
    main()
