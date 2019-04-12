"""
Script that prunes clips from an archive according to detector scores.

For each unique combination of detector, station, and date for which
there are clips, the script deletes clips with scores that are less
than the maximum score for which there are at least `DESIRED_CLIP_COUNT`
clips with at least that score, or no clips if there is no such score.
"""

from collections import defaultdict
from pathlib import Path
import csv
import os
import sqlite3

import numpy as np


DATABASE_FILE_NAME = 'Archive Database.sqlite'

CLIP_COUNTS_QUERY = '''
select
    detector.name Detector,
    station.name Station,
    clip.date Date,
    cast(round(annotation.value, 0) as integer) Score,
    count(*) Clips
from
    vesper_clip as clip
    inner join vesper_string_annotation as annotation
        on clip.id = annotation.clip_id
    inner join vesper_annotation_info as annotation_info
        on annotation.info_id = annotation_info.id
    inner join vesper_processor as detector
        on clip.creating_processor_id = detector.id
    inner join vesper_station as station
        on clip.station_id = station.id
where annotation_info.name = 'Detector Score'
group by Detector, Station, Date, Score;
'''.lstrip()

CLIP_COUNTS_FILE_NAME = 'Detector Clip Counts.csv'

CLIP_COUNTS_FILE_HEADER = ('Detector', 'Station', 'Date', 'Score', 'Clips')

START_SCORES = {
    'BirdVoxDetect 0.1.a0 AT 02': 2,
    'BirdVoxDetect 0.1.a0 AT 05': 5,
    'MPG Ranch Thrush Detector 0.0 40': 40,
    'MPG Ranch Tseep Detector 0.0 40': 40,
}

DESIRED_CLIP_COUNT = 2000

CLIP_IDS_QUERY = '''
select
    clip.id,
    detector.name Detector,
    station.name Station,
    clip.date Date,
    annotation.value Score
from
    vesper_clip as clip
    inner join vesper_processor as detector
        on clip.creating_processor_id = detector.id
    inner join vesper_station as station
        on clip.station_id = station.id
    inner join vesper_string_annotation as annotation
        on clip.id = annotation.clip_id
    inner join vesper_annotation_info as annotation_info
        on annotation.info_id = annotation_info.id
where
    detector.name = ? and
    station.name = ? and
    clip.date = ? and
    annotation_info.name = 'Detector Score' and
    cast(round(annotation.value, 0) as integer) < ?;
'''

# 1000 is too big a delete chunk size for Windows. See
# https://stackoverflow.com/questions/7106016/
# too-many-sql-variables-error-in-django-witih-sqlite3
MAX_DELETE_CHUNK_SIZE = 900


def main():
    
    archive_dir_path = Path.cwd()

    print('Counting clips...')
    clip_counts = get_cumulative_clip_counts(archive_dir_path)
    write_csv_file(archive_dir_path, clip_counts)
    
#     print('Deleting clips...')
#     min_scores = get_min_scores(clip_counts)
#     prune_clips(archive_dir_path, min_scores)
        

def get_cumulative_clip_counts(archive_dir_path):
    
    db_file_path = archive_dir_path / DATABASE_FILE_NAME
    connection = sqlite3.connect(str(db_file_path))
    
    with connection:
        rows = connection.execute(CLIP_COUNTS_QUERY)
    
    counts = defaultdict(create_counts_array)
    
    for detector, station, date, score, count in rows:
        key = (detector, station, date)
        counts[key][score] = count
        
    connection.close()
               
    # Compute cumulative clip count sums so that element i of
    # each count array is the number of clips whose scores are
    # at least i.
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
        
        writer.writerow(CLIP_COUNTS_FILE_HEADER)
        
        keys = sorted(clip_counts.keys())
        for key in keys:
            detector, station, date = key
            counts = clip_counts[key]
            start_score = START_SCORES[detector]
            for score in range(start_score, 101):
                row = (detector, station, date, score, counts[score])
                writer.writerow(row)
                       
        
def get_min_scores(clip_counts):
    return dict(
        (key, get_min_score(counts))
        for key, counts in clip_counts.items())
    
            
def get_min_score(counts):
    
    if counts[0] <= DESIRED_CLIP_COUNT:
        # all counts are less than or equal to threshold
        
        return 0
    
    else:
        # at least one count exceeds threshold
        
        # Find index of last count that is at least threshold. Note that
        # we convert the value returned by `np.searchsorted` to `int`:
        # without this we get an `int64`, which does not play well with
        # SQLite. In particular, substituting an `int64` for an SQLite
        # query parameter does not seem to work properly. No indication
        # that anything is amiss is given, but the query does not return
        # the desired results.
        flipped_counts = np.flip(counts)
        flipped_i = int(np.searchsorted(flipped_counts, DESIRED_CLIP_COUNT))
        return len(counts) - 1 - flipped_i
            
            
def prune_clips(archive_dir_path, min_scores):
                
    # Set up Django.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
    import django
    django.setup()

    from django.db import transaction
    from vesper.django.app.models import Clip

    db_file_path = archive_dir_path / DATABASE_FILE_NAME
    
    keys = sorted(min_scores.keys())
     
    for key in keys:
        
        # Get IDs of clips to delete for this detector, station, and date.
        connection = sqlite3.connect(str(db_file_path))
        min_score = min_scores[key]
        values = key + (min_score,)
        with connection:
            rows = connection.execute(CLIP_IDS_QUERY, values)
            clip_ids = [r[0] for r in rows]
        connection.close()
        
        # Delete clips.
        print(
            'Deleting {} clips for {} / {} / {}...'.format(
                len(clip_ids), *key))
        with transaction.atomic():
            for i in range(0, len(clip_ids), MAX_DELETE_CHUNK_SIZE):
                ids = clip_ids[i:i + MAX_DELETE_CHUNK_SIZE]
                Clip.objects.filter(id__in=ids).delete()
            
            
if __name__ == '__main__':
    main()
