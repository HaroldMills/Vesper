"""
Creates a CSV file of clip counts for a Vesper archive.

The file has the following columns:

    Detector
    Station
    Date
    Classification
    Clips
    
where the "Clips" column contains a clip count for the detector, station,
date, and classification specified in the other columns.

The CSV file is suitable for import into a spreadsheet (e.g. using
Microsoft Excel or Google Sheets) and analysis via, say, a pivot table.
"""


from collections import namedtuple, defaultdict
from pathlib import Path
import csv
import sqlite3
import sys


# TODO: Add mic output name into output.
# TODO: Allow specification of sets of stations/mic output combos, detectors,
#     nights, and classifications.
# TODO: Allow configuration via YAML presets.
# TODO: Add bird counts. This will involve looking at clip times.


DATABASE_FILE_NAME = 'Archive Database.sqlite'

CLIP_COUNTS_FILE_NAME = 'Clip Counts.csv'

CLIP_COUNTS_QUERY = '''
SELECT
    vesper_processor.name Detector,
    vesper_station.name Station,
    date Date,
    value Classification,
    count(*)
FROM
    vesper_clip
LEFT JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
        AND info_id = (
            SELECT id from vesper_annotation_info
            WHERE name = 'Classification')
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_station
    ON vesper_station.id = station_id
GROUP BY
    Detector,
    Station,
    Date,
    Classification
'''.lstrip()

DETECTOR_SUBSTITUTIONS = {
    'Old Bird Thrush Detector Redux 1.1': 'Thrush',
    'Old Bird Tseep Detector Redux 1.1': 'Tseep'
}

CLASSIFICATION_SUBSTITUTIONS = {
    None: 'Unclassified'
}

CSV_FILE_HEADER = ('Detector', 'Station', 'Date', 'Classification', 'Clips')

WILDCARD_COARSE_CLASSIFICATIONS = ('Call', 'FN', 'XCall', 'XCallN', 'XCallP')

Row = namedtuple(
    'Row', ('detector', 'station', 'date', 'classification', 'clip_count'))


def main():
    
    archive_dir_path = Path(sys.argv[1])

    rows = query_database(archive_dir_path)
        
    rows = perform_substitutions(rows)
    
#     print('Query returned {} clip counts.'.format(len(rows)))
#     print()
    
    for coarse_classification in WILDCARD_COARSE_CLASSIFICATIONS:
        rows = add_wildcard_rows(rows, coarse_classification)
    
    write_csv_file(archive_dir_path, rows)
    
#     show_values(rows, 'detector')
#     show_values(rows, 'station')
#     show_values(rows, 'date')
#     show_values(rows, 'classification')
    
    
def query_database(archive_dir_path):
    db_file_path = archive_dir_path / DATABASE_FILE_NAME
    connection = sqlite3.connect(str(db_file_path))
    with connection:
        return connection.execute(CLIP_COUNTS_QUERY)


def perform_substitutions(rows):
    return [perform_substitutions_aux(*r) for r in rows]


def perform_substitutions_aux(
        detector, station, date, classification, clip_count):
            
    detector = DETECTOR_SUBSTITUTIONS.get(detector, detector)
        
    classification = \
        CLASSIFICATION_SUBSTITUTIONS.get(classification, classification)
                
    return Row(detector, station, date, classification, clip_count)

        
def add_wildcard_rows(rows, coarse_classification):
    
    call_counts = defaultdict(int)
    
    for r in rows:
        if r.classification.startswith(coarse_classification):
            key = (r.detector, r.station, r.date)
            call_counts[key] += int(r.clip_count)
            
    new_rows = [
        create_wildcard_row(k, v, coarse_classification)
        for k, v in call_counts.items()]
    
    rows = rows + new_rows
    
    rows.sort()
    
    return rows


def create_wildcard_row(k, v, coarse_classification):
    t = k + (coarse_classification + '*', v)
    return Row(*t)
            
    
def write_csv_file(archive_dir_path, rows):
    
    csv_file_path = archive_dir_path / CLIP_COUNTS_FILE_NAME
    
    with open(csv_file_path, 'w', newline='') as csv_file:
        
        writer = csv.writer(csv_file, delimiter=',', quotechar=None)
        
        writer.writerow(CSV_FILE_HEADER)
        
        for row in rows:
            writer.writerow(row)
            
        
def show_values(rows, attribute_name):
    
    # Get distinct values.
    values = sorted(set([getattr(r, attribute_name) for r in rows]))
    
    # Show.
    print('Distinct {} values:'.format(attribute_name))
    for v in values:
        print('    {}'.format(v))
    print()
    
    
if __name__ == '__main__':
    main()
