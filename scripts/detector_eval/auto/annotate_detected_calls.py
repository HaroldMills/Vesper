"""
Annotates detected calls in a BirdVox-70k archive.

The annotations classify clips created by one or more detectors according
to the archive's ground truth call clips.

This script must be run from the archive directory.
"""


import pandas as pd

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import AnnotationInfo, Processor, User
import vesper.django.app.model_utils as model_utils

import scripts.detector_eval.auto.utils as utils


# Set this `True` to skip actually annotating the detected calls.
# The script will still compute the classifications and print precision,
# recall, and F1 statistics. This is useful for testing purposes, since
# the script runs considerably faster when it doesn't annotate.
ANNOTATE = True

GROUND_TRUTH_DETECTOR_NAME = 'BirdVox-70k'

# The elements of the pairs of numbers are (0) the approximate start offset
# of a call within an Old Bird detector clip, and (1) the approximate
# maximum duration of a call. The units of both numbers are seconds.
DETECTOR_DATA = (
    ('MPG Ranch Tseep Detector 0.0', 'Call.High'),
    ('MPG Ranch Thrush Detector 0.0', 'Call.Low'),
)

CLASSIFICATION_ANNOTATION_NAME = 'Classification'

CENTER_INDEX_ANNOTATION_NAME = 'Call Center Index'
CENTER_FREQ_ANNOTATION_NAME = 'Call Center Freq'

SAMPLE_RATE = 24000


def main():
    
    rows = annotate_detected_calls()
    raw_df = create_raw_df(rows)   
    aggregate_df = create_aggregate_df(raw_df)
    
    add_precision_recall_f1(raw_df)
    add_precision_recall_f1(aggregate_df)
    
    print(raw_df.to_csv())
    print(aggregate_df.to_csv())
        
    
def annotate_detected_calls():
    
    center_index_annotation_info = \
        AnnotationInfo.objects.get(name=CENTER_INDEX_ANNOTATION_NAME)
    center_freq_annotation_info = \
        AnnotationInfo.objects.get(name=CENTER_FREQ_ANNOTATION_NAME)
    classification_annotation_info = \
        AnnotationInfo.objects.get(name=CLASSIFICATION_ANNOTATION_NAME)
        
    user = User.objects.get(username='Vesper')
        
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    
    ground_truth_detector = Processor.objects.get(
        name=GROUND_TRUTH_DETECTOR_NAME)
    
    rows = []
    
    for detector_name, annotation_value in DETECTOR_DATA:
        
        short_detector_name = detector_name.split()[2]
        old_bird_detector = Processor.objects.get(name=detector_name)
        window = utils.CALL_CENTER_WINDOWS[short_detector_name]
                 
        for station, mic_output in sm_pairs:
 
            station_num = int(station.name.split()[1])
            
            print('{} {}...'.format(short_detector_name, station_num))
            
            ground_truth_clips = list(model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                detector=ground_truth_detector,
                annotation_name=CLASSIFICATION_ANNOTATION_NAME,
                annotation_value=annotation_value))
            
            ground_truth_call_center_indices = \
                [c.start_index + c.length // 2 for c in ground_truth_clips]
                          
            ground_truth_call_count = len(ground_truth_clips)

            old_bird_clips = list(model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                detector=old_bird_detector))
            
            old_bird_clip_count = len(old_bird_clips)

            clips = [(c.start_index, c.length) for c in old_bird_clips]
            matches = utils.match_clips_with_calls(
                clips, ground_truth_call_center_indices, window)
            
            old_bird_call_count = len(matches)
            
            rows.append([
                short_detector_name, station_num, ground_truth_call_count,
                old_bird_call_count, old_bird_clip_count])

            if ANNOTATE:
                
                # Clear any existing annotations.
                for clip in old_bird_clips:
                    model_utils.unannotate_clip(
                        clip, classification_annotation_info,
                        creating_user=user)
                    
                # Create new annotations.
                for i, j in matches:
                    
                    old_bird_clip = old_bird_clips[i]
                    call_center_index = ground_truth_call_center_indices[j]
                    ground_truth_clip = ground_truth_clips[j]
                    
                    # Annotate Old Bird clip call center index.
                    model_utils.annotate_clip(
                        old_bird_clip, center_index_annotation_info,
                        str(call_center_index), creating_user=user)
                    
                    # Get ground truth clip call center frequency.
                    annotations = \
                        model_utils.get_clip_annotations(ground_truth_clip)
                    call_center_freq = annotations[CENTER_FREQ_ANNOTATION_NAME]

                    # Annotate Old Bird clip call center frequency.
                    model_utils.annotate_clip(
                        old_bird_clip, center_freq_annotation_info,
                        call_center_freq, creating_user=user)
                
                    model_utils.annotate_clip(
                        old_bird_clip, classification_annotation_info,
                        annotation_value, creating_user=user)
                        
    return rows


def create_raw_df(rows):
    
    columns = [
        'Detector', 'Station', 'Ground Truth Calls', 'Detected Calls',
        'Detected Clips']
    
    return pd.DataFrame(rows, columns=columns)


def create_aggregate_df(df):
    
    data = [
        sum_counts(df, 'Tseep'),
        sum_counts(df, 'Thrush'),
        sum_counts(df, 'All')
    ]
    
    columns = [
        'Detector', 'Ground Truth Calls', 'Detected Calls', 'Detected Clips']
    
    return pd.DataFrame(data, columns=columns)


def sum_counts(df, detector):
    
    if detector != 'All':
        df = df.loc[df['Detector'] == detector]
    
    return [
        detector,
        df['Ground Truth Calls'].sum(),
        df['Detected Calls'].sum(),
        df['Detected Clips'].sum()]
    
        
def add_precision_recall_f1(df):
    p = df['Detected Calls'] / df['Detected Clips']
    r = df['Detected Calls'] / df['Ground Truth Calls']
    df['Precision'] = to_percent(p)
    df['Recall'] = to_percent(r)
    df['F1'] = to_percent(2 * p * r / (p + r))


def to_percent(x):
    return round(1000 * x) / 10


if __name__ == '__main__':
    main()
