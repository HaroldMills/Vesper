"""
Completes a table of clip counts created by a database query.

The table is a CSV file of the results of the SQLite query:

SELECT
    vesper_station.name Station,
    date Date,
    vesper_processor.name Detector,
    value Classification,
    count(*) Clips
FROM
    vesper_clip
LEFT JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id and info_id = 1
INNER JOIN vesper_station
    ON vesper_station.id = station_id
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
GROUP BY
    station_id,
    mic_output_id,
    date,
    vesper_clip.creating_processor_id,
    value;

The resulting table is suitable for import into a spreadsheet
(e.g. with Google Sheets) and analysis via a pivot table.
"""


from collections import namedtuple, defaultdict
from pathlib import Path
import csv


_FILE_PATH = Path((
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/'
    '2017 MPG Ranch Archive Analysis/Clip Counts.csv'))


_DETECTOR_SUBSTITUTIONS = {
    'Old Bird Thrush Detector': 'Thrush',
    'Old Bird Tseep Detector': 'Tseep',
    'Old Bird Thrush Detector Redux 1.1': 'Thrush',
    'Old Bird Tseep Detector Redux 1.1': 'Tseep'
}


_CLASSIFICATION_SUBSTITUTIONS = {
    '': 'Unclassified'
}


Row = namedtuple(
    'Row', ['station', 'date', 'detector', 'classification', 'clip_count'])


def _main():
    
    with open(_FILE_PATH) as csv_file:
        
        reader = csv.reader(csv_file)
        
        # Skip header.
        next(reader)
        
        rows = [Row(*r) for r in reader]
        
        rows = [_perform_substitutions(r) for r in rows]
        
        print('file contained {} rows'.format(len(rows)))
        
        rows += _create_call_star_rows(rows)
        rows.sort()
        
        for r in rows:
            print(
                '{},{},{},{},{}'.format(
                    r.station, r.date, r.detector, r.classification,
                    r.clip_count))

        stations = _get_values(rows, 'station')
        dates = _get_values(rows, 'date')
        detectors = _get_values(rows, 'detector')
        classifications = _get_values(rows, 'classification')
        
        _show(stations, 'stations')
        _show(dates, 'dates')
        _show(detectors, 'detectors')
        _show(classifications, 'classifications')
        
        
def _perform_substitutions(r):
    
    detector = _DETECTOR_SUBSTITUTIONS.get(r.detector, r.detector)
    
    classification = _CLASSIFICATION_SUBSTITUTIONS.get(
        r.classification, r.classification)
        
    return Row(r.station, r.date, detector, classification, int(r.clip_count))
    
    
def _create_call_star_rows(rows):
    
    call_counts = defaultdict(int)
    
    for r in rows:
        if r.classification.startswith('Call'):
            key = (r.station, r.date, r.detector)
            call_counts[key] += int(r.clip_count)
            
    return [_create_call_star_row(k, v) for k, v in call_counts.items()]


def _create_call_star_row(k, v):
    t = k + ('Call*', v)
    return Row(*t)
            
    
def _get_values(rows, attribute_name):
    return sorted(set([getattr(r, attribute_name) for r in rows]))


def _show(items, name):
    print('{}:'.format(name))
    for i in items:
        print(i)
    print()
    

if __name__ == '__main__':
    _main()
