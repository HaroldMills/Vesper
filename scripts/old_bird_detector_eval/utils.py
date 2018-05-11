from pathlib import Path


BIRDVOX_70K_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/BirdVox/BirdVox-70k')

BIRDVOX_70K_ARCHIVE_DIR_PATH = BIRDVOX_70K_DIR_PATH / 'Vesper Archive'

BIRDVOX_70K_ARCHIVE_RECORDINGS_DIR_PATH = \
    BIRDVOX_70K_ARCHIVE_DIR_PATH / 'Recordings'

BIRDVOX_70K_UNIT_CLIPS_CSV_FILES_DIR_PATH = \
    BIRDVOX_70K_DIR_PATH / 'Other' / 'Unit Clips CSV Files'
    
OLD_BIRD_CLIPS_FILE_PATH = Path('/Users/harold/Desktop/Old Bird Clips.csv')

MIN_DETECTION_THRESHOLD = 1.05
MAX_DETECTION_THRESHOLD = 20
DETECTION_THRESHOLDS_POWER = 3
NUM_DETECTION_THRESHOLDS = 50

# Center frequency threshold separating tseep and thrush calls, in hertz.
FREQ_THRESHOLD = 5000

# Recording sample rate, in hertz.
SAMPLE_RATE = 24000


def seconds_to_samples(x):
    return int(round(x * SAMPLE_RATE))


OLD_BIRD_CLIP_CALL_CENTER_WINDOWS = {
    'Tseep': (seconds_to_samples(.09), seconds_to_samples(.2)),
    'Thrush': (seconds_to_samples(.15), seconds_to_samples(.2))
}


def match_clips_with_calls(clips, call_center_indices, window):
    
    clip_count = len(clips)
    
    matches = []
    i = 0
    
    for j, call_center_index in enumerate(call_center_indices):
        
        while i != clip_count and \
                get_end_index(clips[i]) <= call_center_index:
            # Old Bird clip i ends before call center
            
            i += 1
            
        if i == clip_count:
            # no more Old Bird clips
            
            break
            
        # At this point Old Bird clip i is the first Old Bird clip
        # that has not already been paired with a call center and
        # that ends after call center j.
        
        if is_call_detection(clips[i], call_center_index, window):
                
            matches.append((i, j))
            # Increment i to ensure that we match each Old Bird clip
            # with at most one ground truth call. This is conservative,
            # since some Old Bird clips contain more than one ground
            # truth call.
            i += 1
            
    return matches
            

def get_end_index(clip):
    start_index, length = clip
    return start_index + length


# Tests if the specified Old Bird clip should count as a detection of
# a call with the specified center index, i.e. if the center index is
# within the specified detection window within the clip.
def is_call_detection(clip, call_center_index, window):
    clip_start_index, clip_length = clip
    clip_end_index = clip_start_index + clip_length
    window_start_offset, window_length = window
    window_start_index = clip_start_index + window_start_offset
    window_end_index = min(window_start_index + window_length, clip_end_index)
    return window_start_index <= call_center_index and \
        call_center_index < window_end_index
