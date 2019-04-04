"""
Script that creates a CSV file of clip counts by detector, station, date,
and detector score.
"""


from collections import defaultdict
from pathlib import Path
import csv
import sqlite3
import sys

import numpy as np


DATABASE_FILE_NAME = 'Archive Database.sqlite'

CLIP_COUNTS_FILE_NAME = 'Detector Clip Counts.csv'

QUERY = '''
select
    detector.name Detector,
    station.name Station,
    clip.date Date,
    annotation.value Score
from
    vesper_clip as clip
    inner join vesper_string_annotation as annotation
        on clip.id = annotation.clip_id
    inner join vesper_processor as detector
        on clip.creating_processor_id = detector.id
    inner join vesper_station as station
        on clip.station_id = station.id
where annotation.info_id = 2;
'''.lstrip()

DETECTOR_SUBSTITUTIONS = {
    'MPG Ranch Tseep Detector 0.0 40': 'MPG Ranch Tseep',
    'BirdVoxDetect 0.1.a0 AT 02': 'BirdVoxDetect',
    'BirdVoxDetect 0.1.a0 AT 05': 'BirdVoxDetect',
}

CSV_FILE_HEADER = ('Detector', 'Station', 'Date', 'Score', 'Clips')

START_SCORES = {
    'MPG Ranch Tseep': 40,
    'BirdVoxDetect': 5
}


def main():
    
    archive_dir_path = Path(sys.argv[1])

    rows = query_database(archive_dir_path)
    
    rows = perform_substitutions(rows)
    
    clip_counts = count_clips(rows)
    
    write_csv_file(archive_dir_path, clip_counts)
        

def query_database(archive_dir_path):
    db_file_path = archive_dir_path / DATABASE_FILE_NAME
    connection = sqlite3.connect(str(db_file_path))
    with connection:
        return connection.execute(QUERY)


def perform_substitutions(rows):
    return [perform_substitutions_aux(*r) for r in rows]


def perform_substitutions_aux(detector, station, date, score):
    detector = DETECTOR_SUBSTITUTIONS.get(detector, detector)
    return (detector, station, date, score)

        
def count_clips(rows):
    
    counts = defaultdict(create_counts_array)
    
    # Count scores by detector, station, date, and rounded score.
    for detector, station, date, score in rows:
        key = (detector, station, date)
        score = round(float(score))
        counts[key][score] += 1
        
    # Compute cumulative count sums, so that element i of a counts array
    # is the number of clips whose scores are at least i.
    counts = dict(
        (key, np.flip(np.cumsum(np.flip(value))))
        for key, value in counts.items())

    return counts


def create_counts_array():
    return np.zeros(101, dtype='int32')


def write_csv_file(archive_dir_path, clip_counts):
    
    csv_file_path = archive_dir_path / CLIP_COUNTS_FILE_NAME
    
    with open(csv_file_path, 'w') as csv_file:
        
        writer = csv.writer(csv_file, delimiter=',', quotechar=None)
        
        writer.writerow(CSV_FILE_HEADER)
        
        keys = sorted(clip_counts.keys())
        for key in keys:
            detector, station, date = key
            counts = clip_counts[key]
            start_score = START_SCORES[detector]
            for score in range(start_score, 101):
                row = (detector, station, date, score, counts[score])
                print(row)
                writer.writerow(row)
                       
        
if __name__ == '__main__':
    main()
