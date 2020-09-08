"""Tags 2018 MPG Ranch archive clips."""


from collections import defaultdict
from pathlib import Path
import datetime
import random
import sqlite3


BASE_DIR_PATH = Path('/Users/harold/Desktop/NFC/Data/MPG Ranch/2018')
ARCHIVE_DIR_NAME_FORMAT = 'Part {}'
DATABASE_FILE_NAME = 'Archive Database.sqlite'

TAG = 'Tseep Classification Dataset'
EXCLUDED_TAGS = []
MAX_TAGGED_CLIP_COUNT = 1000

DELETE_TAG_EDITS_QUERY = 'DELETE FROM vesper_tag_edit WHERE info_id = ?'
DELETE_TAGS_QUERY = 'DELETE FROM vesper_tag WHERE info_id = ?'
DELETE_TAG_INFO_QUERY = 'DELETE FROM vesper_tag_info WHERE id = ?'

CLASSIFICATION_QUERY = '''
SELECT DISTINCT
    value Classification
FROM
    vesper_clip
INNER JOIN vesper_tag
    ON vesper_clip.id = vesper_tag.clip_id
INNER JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
WHERE
    vesper_clip.creating_processor_id = (
        SELECT id from vesper_processor
        WHERE name = 'Old Bird Tseep Detector Redux 1.1')
    AND vesper_tag.info_id = (
        SELECT id from vesper_tag_info
        WHERE name = 'Tseep Classification Dataset')
    AND vesper_string_annotation.info_id = (
        SELECT id from vesper_annotation_info
        WHERE name = 'Classification')
    AND vesper_string_annotation.value LIKE 'Call.%'
    ORDER BY value
'''.lstrip()

# TODO: Handle processor in queries below as in query above.

ALL_CLIPS_QUERY = '''
SELECT
    vesper_clip.id
FROM
    vesper_clip
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
WHERE
    vesper_processor.name = 'Old Bird Tseep Detector Redux 1.1'
    AND vesper_string_annotation.info_id = (
        SELECT id from vesper_annotation_info
        WHERE name = 'Classification')
    AND vesper_string_annotation.value = '{}'
'''.lstrip()

TAGGED_CLIPS_QUERY = '''
SELECT
    vesper_clip.id
FROM
    vesper_clip
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
INNER JOIN vesper_tag
    ON vesper_clip.id = vesper_tag.clip_id
WHERE
    vesper_processor.name = 'Old Bird Tseep Detector Redux 1.1'
    AND vesper_string_annotation.info_id = (
        SELECT id from vesper_annotation_info
        WHERE name = 'Classification')
    AND vesper_string_annotation.value = '{}'
    AND vesper_tag.info_id = (
        SELECT id from vesper_tag_info
        WHERE name = '{}')
'''.lstrip()

TAG_INFO_QUERY = 'SELECT id FROM vesper_tag_info WHERE name = ?'

INSERT_TAG_INFO_QUERY = '''
INSERT INTO vesper_tag_info(name, description, creation_time) VALUES (?, ?, ?)
'''.strip()

INSERT_TAG_QUERY = '''
INSERT INTO vesper_tag(clip_id, info_id, creation_time) VALUES (?, ?, ?)
'''.strip()

INSERT_TAG_EDIT_QUERY = '''
INSERT INTO
    vesper_tag_edit(clip_id, info_id, action, creation_time)
VALUES (?, ?, ?, ?)
'''.strip()

TOTAL_CALL_COUNTS_QUERY = '''
SELECT
    value Classification,
    count(*)
FROM
    vesper_clip
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
WHERE
    vesper_processor.name = 'Old Bird Tseep Detector Redux 1.1'
    AND vesper_string_annotation.info_id = (
        SELECT id from vesper_annotation_info
        WHERE name = 'Classification')
    AND vesper_string_annotation.value LIKE 'Call.%'
GROUP BY
    Classification
'''.lstrip()

TAGGED_CALL_COUNTS_QUERY = '''
SELECT
    value Classification,
    count(*)
FROM
    vesper_clip
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
INNER JOIN vesper_tag
    ON vesper_tag.clip_id = vesper_clip.id
WHERE
    vesper_processor.name = 'Old Bird Tseep Detector Redux 1.1'
    AND vesper_string_annotation.info_id = (
        SELECT id from vesper_annotation_info
        WHERE name = 'Classification')
    AND vesper_string_annotation.value LIKE 'Call.%'
    AND vesper_tag.info_id = (
        SELECT id from vesper_tag_info
        WHERE name = 'Classification Dataset')
GROUP BY
    Classification
'''.lstrip()


'''
Max Count,Total Clips,Classifications
1000,17108,14
2000,29949,11
3000,40005,9
4000,48556,8
5000,56556,8
10000,94520,6
20000,140593,4
30000,180593,4
40000,220593,4
50000,251316,3
'''


'''
Tasks:

    * Tag Call.* clips, possibly excluding those with specified existing
      tags, with or without a per-class max clip count.
      
    * Clear tag (i.e. delete tags but not tag info).
    
    * Delete tag (i.e. delete tags and tag info).
    
    * Merge one set of tagged clips into another (i.e. re-tag clips with
      one tag with another).


Get Clip.* classifications.

For each classification:

    Get clips.
    Get clips for excluded tags.
    Get non-excluded tags (by set subtraction).
    Select clips to be tagged (at random from non-excluded tags).
    Tag clips.
'''


def main():
    
    delete_tag('Classification Dataset')
    
    # tag_clips(TAG, EXCLUDED_TAGS, MAX_TAGGED_CLIP_COUNT)
    
    # show_clips(TAG)
    
    
def delete_tag(tag):
    for part_num in (1, 2):
        delete_part_tag(part_num, tag)
        
        
def delete_part_tag(part_num, tag):
    
    connection = create_db_connection(part_num)
    
    with connection:
        
        cursor = connection.cursor()
        
        info_id = get_tag_info_id(cursor, tag)
        
        if info_id is not None:
            cursor.execute(DELETE_TAG_EDITS_QUERY, (info_id,))
            cursor.execute(DELETE_TAGS_QUERY, (info_id,))
            cursor.execute(DELETE_TAG_INFO_QUERY, (info_id,))
        
        
def create_db_connection(part_num):
    path = get_db_file_path(part_num)
    return sqlite3.connect(str(path))


def get_db_file_path(part_num):
    archive_dir_name = ARCHIVE_DIR_NAME_FORMAT.format(part_num)
    return BASE_DIR_PATH / archive_dir_name / DATABASE_FILE_NAME


def get_tag_info_id(cursor, tag):
    
    cursor.execute(TAG_INFO_QUERY, (tag,))
    row = cursor.fetchone()
    
    if row is None:
        return None
    else:
        return row[0]
    

def tag_clips(tag, excluded_tags, max_count):
    
    create_tag_if_needed(tag)
    
    classifications = get_classifications()
    
    for classification in classifications:
        
        clips = get_clips(classification, excluded_tags)
        
        # Select random subset of clips if needed.
        if len(clips) > max_count:
            clips = random.sample(clips, max_count)
            
        # Partition clips by archive part number.
        part_clip_ids = partition_clips(clips)
        
        # Tag clips one archive part at a time.
        for part_num, clip_ids in part_clip_ids.items():
            tag_part_clips(part_num, tag, clip_ids)
            
        print(f'{classification} {len(clips)}')
        
    
def create_tag_if_needed(tag):
    for part_num in (1, 2):
        create_part_tag_if_needed(part_num, tag)

 
def create_part_tag_if_needed(part_num, tag):
    
    connection = create_db_connection(part_num)
    
    with connection:
        
        cursor = connection.cursor()
        
        info_id = get_tag_info_id(cursor, tag)
        
        if info_id is None:
            # tag does not already exist
            
            description = ''
            creation_time = datetime.datetime.now()
            
            info = (tag, description, creation_time)
            cursor.execute(INSERT_TAG_INFO_QUERY, info)
    
    
def get_classifications():
    classifications_1 = get_part_classifications(1)
    classifications_2 = get_part_classifications(2)
    classifications = classifications_1 | classifications_2
    return sorted(classifications)
    
    
def get_part_classifications(part_num):
    
    connection = create_db_connection(part_num)
    
    with connection:
        rows = connection.execute(CLASSIFICATION_QUERY)
        
    return frozenset(r[0] for r in rows)
    
    
def get_clips(classification, excluded_tags):
    
    clips = get_all_clips(classification)
    
    for tag in excluded_tags:
        excluded_clips = get_tagged_clips(classification, tag)
        clips -= excluded_clips
        
    return clips


def get_all_clips(classification):
    clips_1 = execute_all_clips_query(1, classification)
    clips_2 = execute_all_clips_query(2, classification)
    return clips_1 | clips_2


def execute_all_clips_query(part_num, classification):
    query = ALL_CLIPS_QUERY.format(classification)
    return execute_clip_query(part_num, query)


def execute_clip_query(part_num, query):
    connection = create_db_connection(part_num)
    with connection:
        rows = connection.execute(query)
    return create_clip_set(part_num, rows)


def create_clip_set(part_num, rows):
    return frozenset((part_num, r[0]) for r in rows)
    
    
def get_tagged_clips(classification, tag):
    clips_1 = execute_tagged_clips_query(1, classification, tag)
    clips_2 = execute_tagged_clips_query(2, classification, tag)
    return clips_1 | clips_2


def execute_tagged_clips_query(part_num, classification, tag):
    query = TAGGED_CLIPS_QUERY.format(classification, tag)
    return execute_clip_query(part_num, query)
    
    
def partition_clips(clips):
    
    partitions = defaultdict(list)
    
    for part_num, clip_id in clips:
        partitions[part_num].append(clip_id)
        
    return partitions
    
    
def tag_part_clips(part_num, tag, clip_ids):
    
    connection = create_db_connection(part_num)
    
    with connection:
        
        cursor = connection.cursor()
        
        tag_info_id = get_tag_info_id(cursor, tag)
        creation_time = datetime.datetime.now()
        
        values = [
            (clip_id, tag_info_id, creation_time)
            for clip_id in clip_ids]
        
        cursor.executemany(INSERT_TAG_QUERY, values)
        
        values = [
            (clip_id, tag_info_id, 'S', creation_time)
            for clip_id in clip_ids]
        
        cursor.executemany(INSERT_TAG_EDIT_QUERY, values)
        
        
        
        
    
    
def show_clips(tag):
    
    classifications = get_classifications()
    
    print(f'{tag} clips:')
    
    for classification in classifications:
        
        clips = sorted(get_tagged_clips(classification, tag))
        
        print(f'    {classification} {len(clips)}')
        
        



def get_call_counts(name, query):
    
    counts_1 = get_part_call_counts(1, query)
    show_clip_counts(f'Part 1 {name}', counts_1)
    
    counts_2 = get_part_call_counts(2, query)
    show_clip_counts(f'Part 2 {name}', counts_2)
    
    counts = sum_clip_counts(counts_1, counts_2)
    show_clip_counts(f'Both parts {name}', counts)
    
    return counts


def get_part_call_counts(part_num, query):
    return execute_clip_count_query(part_num, query)
    
    
def execute_clip_count_query(part_num, query):
    
    connection = create_db_connection(part_num)
    
    with connection:
        rows = connection.execute(query)
        
    return dict(r for r in rows)
    
    
def show_clip_counts(name, counts):
    
    print(f'{name}:')
    
    total = 0
    items = sorted(counts.items())
    
    for classification, count in items:
        print(f'    {classification}: {count}')
        total += count
        
    print(f'    Total: {total}')
        
        
def sum_clip_counts(*args):
    counts = defaultdict(int)
    for count_dict in args:
        accumulate_clip_counts(count_dict, counts)
    return counts
    
    
def accumulate_clip_counts(counts, totals):
    for classification, count in counts.items():
        totals[classification] += count
       

def get_tagged_clip_count_adjustments(
        total_clip_counts, tagged_clip_counts, max_tagged_clip_count):
    
    adjustments = {}
    
    items = sorted(total_clip_counts.items())
    
    for classification, total_count in items:
        
        tagged_count = tagged_clip_counts.get(classification, 0)
        
        if tagged_count > max_tagged_clip_count:
            adjustment = tagged_count - max_tagged_clip_count
            
        else:
            desired_count = min(total_count, max_tagged_clip_count)
            adjustment = desired_count - tagged_count
            
        if adjustment != 0:
            adjustments[classification] = adjustment
            
    return adjustments


if __name__ == '__main__':
    main()
