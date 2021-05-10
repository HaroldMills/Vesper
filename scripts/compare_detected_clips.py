"""Compares clips created by two detectors."""


from pathlib import Path
import csv
import datetime

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import (
    AnnotationInfo, Clip, Device, Processor, Station, StringAnnotation)
import vesper.util.time_utils as time_utils


DETECTORS = (
    # ('Old Bird Tseep Detector', 'Original'),
    # ('Old Bird Tseep Detector Redux 1.1', 'Redux'),
    ('Old Bird Thrush Detector', 'Original'),
    ('Old Bird Thrush Detector Redux 1.1', 'Redux'),
)

STATION_MIC_PAIRS = (
    ('Station 1', '21c 1'),
    ('Station 2', '21c 2'),
    ('Station 3', '21c 3'),
    ('Station 4', '21c 4'),
    ('Station 5', '21c 5'),
    ('Station 6', '21c 6'),
    ('Station 7', '21c 7'),
)

START_DATE = datetime.date(2016, 4, 1)
END_DATE = datetime.date(2016, 6, 30)

OUTPUT_FILE_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Old Bird/Lighthouse/'
    'Lighthouse 2016 Old Bird Detector Comparison Archive/'
    'Old Bird Thrush Detector Comparison.csv')

OUTPUT_FILE_HEADER_FORMAT = (
    'Station / Mic,Date,'
    '{} Clips,{} Clips,'
    'Perfect Matches,Imperfect Matches,'
    'Unmatched {} Clips,Unmatched {} Clips')

ONE_DAY = datetime.timedelta(days=1)


def main():

    compare_clips()
    
    # annotate_differing_clips()
    
    # test_match_clips_aux()
    
    
def compare_clips():
    
    with open(OUTPUT_FILE_PATH, 'w', newline='') as csv_file:
        
        writer = csv.writer(csv_file)
        
        ((detector_a_name, detector_a_short_name),
         (detector_b_name, detector_b_short_name)) = DETECTORS
         
        detector_a = Processor.objects.get(name=detector_a_name)
        detector_b = Processor.objects.get(name=detector_b_name)
        
        write_output_header(
            writer, detector_a_short_name, detector_b_short_name)
        
        for station_name, mic_name in STATION_MIC_PAIRS:
            
            station = Station.objects.get(name=station_name)
        
            mic = Device.objects.get(name=mic_name)
            mic_output = mic.outputs.all()[0]
            
            date = START_DATE
            
            while date <= END_DATE:
                
                print(f'{station_name} / {mic_name} {str(date)}...')
                
                clip_pairs = match_clips(
                    station, mic_output, date, detector_a, detector_b)
                
                write_output_row(writer, station, mic_output, date, clip_pairs)
                
                date += ONE_DAY
    
    
def write_output_header(writer, detector_a_short_name, detector_b_short_name):
    a = detector_a_short_name
    b = detector_b_short_name
    header = OUTPUT_FILE_HEADER_FORMAT.format(a, b, a, b, a, b).split(',')
    writer.writerow(header)
    
    
def match_clips(station, mic_output, date, detector_a, detector_b):
    
    clips_a = get_clips(station, mic_output, date, detector_a)
    clips_b = get_clips(station, mic_output, date, detector_b)
    
    bounds_a = get_clip_bounds(clips_a)
    bounds_b = get_clip_bounds(clips_b)
    
    index_pairs = match_clips_aux(bounds_a, bounds_b)
    
    clip_pairs = get_clip_pairs(index_pairs, clips_a, clips_b)
    
    return clip_pairs


def get_clips(station, mic_output, date, detector):
    return tuple(
        Clip.objects.filter(
            station=station,
            mic_output=mic_output,
            date=date,
            creating_processor=detector
        ).order_by('start_index'))


def get_clip_bounds(clips):
    return [(c.start_index, c.end_index) for c in clips]

    
def match_clips_aux(a, b):
    
    m = len(a)
    n = len(b)
    
    i = 0
    j = 0
    pairs = []

    while i < m:
        
        # Find first b clip whose end is at least start of a[i], noting
        # unmatched b clips along the way.
        while j < n and b[j][1] <= a[i][0]:
            pairs.append((None, j))
            j += 1
            
        # Match all b clips that intersect a[i] with a[i].
        matched = False
        while j < n and b[j][0] <= a[i][1]:
            pairs.append((i, j))
            j += 1
            matched = True
            
        # If no b clips were matched with a[i], note that a[i] is unmatched.
        if not matched:
            pairs.append((i, None))
            
        i += 1
        
    # Note that remaining b clips are unmatched.
    while j < n:
        pairs.append((None, j))
        j += 1
        
    return pairs
            
        
def get_clip_pairs(index_pairs, clips_a, clips_b):
    return [get_clip_pair(p, clips_a, clips_b) for p in index_pairs]


def get_clip_pair(index_pair, clips_a, clips_b):
    i, j = index_pair
    clip_a = get_clip(i, clips_a)
    clip_b = get_clip(j, clips_b)
    return clip_a, clip_b


def get_clip(index, clips):
    if index is None:
        return None
    else:
        return clips[index]


def write_output_row(writer, station, mic_output, date, clip_pairs):
    
    
    # Match clips.
    
    a_count = 0
    b_count = 0
    perfect_match_count = 0
    imperfect_match_count = 0
    unmatched_a_count = 0
    unmatched_b_count = 0
    
    for clip_a, clip_b in clip_pairs:
        
        if clip_a is not None and clip_b is not None:
            # matching clips
            
            a_count += 1
            b_count += 1
                
            if clip_a.start_index == clip_b.start_index and \
                    clip_a.end_index == clip_b.end_index:
                # match is perfect
                
                perfect_match_count += 1
                
            else:
                # match is imperfect
                
                imperfect_match_count += 1
                
        elif clip_a is not None and clip_b is None:
            # unmatched a clip
            
            a_count += 1
            unmatched_a_count += 1
            
        elif clip_a is None and clip_b is not None:
            # unmatched b clip
            
            b_count += 1
            unmatched_b_count += 1
            
        else:
            # this should not happen
            
            raise Exception('Unexpected (None, None) clip pair.')
            
            
    # Check consistency of clip and match counts.
    matched_count = 2 * (perfect_match_count + imperfect_match_count)
    unmatched_count = unmatched_a_count + unmatched_b_count
    assert(a_count + b_count == matched_count + unmatched_count)
    
    
    # Write output file row.
    
    if a_count != 0 or b_count != 0:
        # have clips for this detector_pair-station-mic-date
        
        station_mic_name = f'{station.name} / {mic_output.device.name}'
        
        writer.writerow((
            station_mic_name, str(date),
            a_count, b_count,
            perfect_match_count, imperfect_match_count,
            unmatched_a_count, unmatched_b_count))
    
    
def annotate_differing_clips():
    
    for _, detector_a_name, detector_b_name in DETECTORS:
        
        detector_a = Processor.objects.get(name=detector_a_name)
        detector_b = Processor.objects.get(name=detector_b_name)
        
        for station_name, mic_name in STATION_MIC_PAIRS:
            
            station = Station.objects.get(name=station_name)
        
            mic = Device.objects.get(name=mic_name)
            mic_output = mic.outputs.all()[0]
            
            date = START_DATE
            
            while date <= END_DATE:
                
                clip_pairs = match_clips(
                    station, mic_output, date, detector_a, detector_b)
                
                for clip_a, clip_b in clip_pairs:
                    
                    if clip_a is None:
                        annotate_clip(clip_b, 'Unmatched')
                        
                    elif clip_b is None:
                        annotate_clip(clip_a, 'Unmatched')
                        
                    elif clip_a.start_index != clip_b.start_index or \
                            clip_a.length != clip_b.length:
                        annotate_clip(clip_a, 'Different')
                        annotate_clip(clip_b, 'Different')
                        
                date += ONE_DAY

    
def annotate_clip(clip, annotation_value):
    
    annotation_info = AnnotationInfo.objects.get(name='Classification')
    creation_time = time_utils.get_utc_now()
    
    try:
        StringAnnotation.objects.create(
            clip=clip,
            info=annotation_info,
            value=annotation_value,
            creation_time=creation_time)
        
    except Exception:
        
        # This can happen if a clip from one detector overlaps two or
        # more clips from another detector.
        pass

    
def test_match_clips_aux():
    
    cases = [
        
        # no clips
        ([], [], []),
         
        # perfect matches
        ([(1, 2)], [(1, 2)], [(0, 0)]),
        ([(1, 2), (3, 4)], [(1, 2), (3, 4)], [(0, 0), (1, 1)]),
          
        # imperfect matches
        ([(1, 2)], [(1, 3)], [(0, 0)]),
        ([(1, 2), (5, 6)], [(1, 3), (4, 6)], [(0, 0), (1, 1)]),
         
        # unmatched clips
        ([(1, 2)], [], [(0, None)]),
        ([], [(1, 2)], [(None, 0)]),
        ([(1, 2)], [(3, 4)], [(0, None), (None, 0)]),
        ([(1, 2), (7, 8)], [(3, 4), (5, 6)],
         [(0, None), (None, 0), (None, 1), (1, None)]),
         
        # matching and unmatched clips
        ([(1, 2), (3, 4), (7, 8)], [(3, 4), (5, 6), (7, 8)],
         [(0, None), (1, 0), (None, 1), (2, 2)])
        
    ]
    
    for a, b, expected in cases:
        result = match_clips_aux(a, b)
        if result != expected:
            print('Test failed.')
            print('result:', result)
            print('expected:', expected)
            return
        
    print('Test succeeded.')
        
    
def create_pairs(a, b, pairs):
    return [create_pair(a, b, *p) for p in pairs]


def create_pair(a, b, a_index, b_index):
    return (index(a, a_index), index(b, b_index))


def index(a, i):
    return None if i is None else a[i]


if __name__ == '__main__':
    main()
