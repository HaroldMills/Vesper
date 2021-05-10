"""
Script that analyzes the classification edits of an archive.

The analysis focuses on changes user "dleick" made to classifications
created by user "cvoss", in order to inform decisions about how to most
efficiently direct classification effort.
"""


from collections import defaultdict
import sqlite3

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import AnnotationInfo, Processor, User


ANNOTATION_NAME = 'Classification'

DETECTOR_NAMES = frozenset([
    'BirdVoxDetect 0.1.a0 AT 05',
    'MPG Ranch Thrush Detector 0.0 40',
    'MPG Ranch Tseep Detector 0.0 40'
])

DATABASE_FILE_NAME = 'Archive Database.sqlite'

QUERY = '''
select e.clip_id, e.action, e.value, e.creating_user_id, e.creation_time
from vesper_string_annotation_edit as e
    join vesper_clip as c on e.clip_id = c.id
where c.creating_processor_id = ?
    and e.info_id = ?
    and e.creation_time >= ?;
'''

START_DATE = '2019-04-01'


def main():
    
    annotation_info = AnnotationInfo.objects.get(name=ANNOTATION_NAME)
    users = get_users()

    for processor in Processor.objects.all():
        
        if processor.name in DETECTOR_NAMES:
            
            print('{}:'.format(processor.name))
            
            edits = get_classification_edits(processor.id, annotation_info.id)
            analyze_edits(edits, users)
            
            
def get_users():
    return dict((u.id, u.username) for u in User.objects.all())


def get_classification_edits(detector_id, annotation_info_id):
    
    connection = sqlite3.connect(DATABASE_FILE_NAME)
    
    values = (detector_id, annotation_info_id, START_DATE)
    
    with connection:
        rows = connection.execute(QUERY, values)
    
    edits = defaultdict(list)
     
    for clip_id, action, value, user_id, time in rows:
        edits[clip_id].append((action, value, user_id, time))
         
    connection.close()
    
    return edits
               

def analyze_edits(edit_lists, user_names):
    
    history_counts = count_edit_histories(edit_lists, user_names)
    
    change_counts = count_changes(history_counts)
                
#     print('    history counts:')
#     histories = sorted(history_counts.keys())
#     for history in histories:
#         print('       {} {}'.format(history, history_counts[history]))
        
    print("    Debbie's classification change counts:")
    changes = sorted(change_counts.keys())
    for old, new in changes:
        count = change_counts[(old, new)]
        print('        {} -> {} {}'.format(old, new, count))
        
    num_changes = sum(change_counts.values())
    total_num_clips = sum(history_counts.values())
    changed_percent = 100 * num_changes / total_num_clips
    print((
        "    Debbie changed Carrie's classifications for {} of {} clips, "
        'or {:.1f} percent.').format(
            num_changes, total_num_clips, changed_percent))


def count_edit_histories(edit_lists, user_names):
    
    counts = defaultdict(int)
    
    clip_ids = sorted(edit_lists.keys())
    for clip_id in clip_ids:
        edits = edit_lists[clip_id]
        histories = tuple([get_count_key(e, user_names) for e in edits])
        counts[histories] += 1

    return counts


def get_count_key(edit, user_names):
    
    action, classification, user_id, _ = edit
    
    if user_id is None:
        user_name = 'transfer'
    else:
        user_name = user_names[user_id]
        
    if action == 'S':
        return (user_name, classification)
    
    elif action == 'D':
        return (user_name, 'Unclassified')
    
    else:
        raise ValueError('Unrecognized edit action "{}".'.format(action))
    
    
def count_changes(history_counts):
    
    change_counts = defaultdict(int)
    
    for edits, count in history_counts.items():
        
        if edits[-1][0] == 'dleick':
            # Debbie made final edit in this history
            
            debbie_classification = edits[-1][1]
            
            i = find_final_carrie_edit(edits)
            
            if i == -1:
                # history includes no Carrie edits
                
                accumulate_change_count(
                    change_counts, 'Unclassified', debbie_classification,
                    count)
                
            else:
                # history includes at least one Carrie edit
                
                carrie_classification = edits[i][1]
                
                accumulate_change_count(
                    change_counts, carrie_classification,
                    debbie_classification, count)
                        
    return change_counts


def find_final_carrie_edit(edits):
    
    for i, (name, _) in enumerate(reversed(edits)):
        if name == 'cvoss':
            return len(edits) - i - 1
        
    return -1
        
                
def accumulate_change_count(change_counts, old, new, count):
    if new != old and not (old == 'Unclassified' and new == 'Noise'):
        change_counts[(old, new)] += count


if __name__ == '__main__':
    main()
