"""
Compares clips created by two detectors for a particular station, microphone,
and date.
"""


import csv
import datetime
import io
import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.models import (
    AnnotationInfo, Clip, Device, Processor, Station, StringAnnotation)
import vesper.util.time_utils as time_utils


DETECTOR_PAIRS = (
    
    ('Old Bird Tseep Detector',
     'Old Bird Tseep Detector Redux 1.1'),
                  
    ('Old Bird Thrush Detector',
     'Old Bird Thrush Detector Redux 1.1')
                  
)

STATION_NAMES = ('Floodplain',)
MIC_NAMES = ('21c Floodplain', 'SMX-NFC Floodplain')
START_DATE = datetime.date(2016, 8, 22)
END_DATE = datetime.date(2016, 8, 22)

# DETECTOR_PAIRS = (
#     ('Old Bird Tseep Detector', 'Old Bird Tseep Detector Redux 1.0'),
#     ('Old Bird Thrush Detector', 'Old Bird Thrush Detector Redux 1.0'),
# )
# STATION_NAMES = ('Floodplain',)
# MIC_NAMES = ('21c 0', 'SMX-NFC 2')
# START_DATE = datetime.date(2016, 8, 22)
# END_DATE = datetime.date(2016, 8, 25)

ONE_DAY = datetime.timedelta(days=1)


def main():

    # annotate_differing_clips()
    
    show_clip_diffs()
    
    # test_pair_clips_aux()
    
    
def annotate_differing_clips():
    
    for detector_a_name, detector_b_name in DETECTOR_PAIRS:
        
        detector_a = Processor.objects.get(name=detector_a_name)
        detector_b = Processor.objects.get(name=detector_b_name)
                    
        for station_name in STATION_NAMES:
            
            station = Station.objects.get(name=station_name)
        
            for mic_name in MIC_NAMES:
                
                mic = Device.objects.get(name=mic_name)
                mic_output = mic.outputs.all()[0]
                
                date = START_DATE
                
                while date <= END_DATE:
                                        
                    clip_pairs = pair_clips(
                        station, mic_output, date, detector_a, detector_b)
                    
                    for clip_a, clip_b in clip_pairs:
                        
                        if clip_a is None:
                            annotate_clip(clip_b, 'Unpaired')
                            
                        elif clip_b is None:
                            annotate_clip(clip_a, 'Unpaired')
                            
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

    
CSV_FILE_HEADER = (
    'Station',
    'Mic Output',
    'Date',
    'Detector A',
    'Detector B',
    'A Clips',
    'B Clips',
    'Differing Clips',
    'Unpaired A Clips',
    'Unpaired B Clips',
    'Differing Clips Percent',
    'Unpaired A Clips Percent',
    'Unpaired B Clips Percent'
)


def show_clip_diffs():
    
    string = io.StringIO(newline='')
    writer = csv.writer(string)
    writer.writerow(CSV_FILE_HEADER)
    
    for detector_a_name, detector_b_name in DETECTOR_PAIRS:
        
        detector_a = Processor.objects.get(name=detector_a_name)
        detector_b = Processor.objects.get(name=detector_b_name)
                    
        for station_name in STATION_NAMES:
            
            station = Station.objects.get(name=station_name)
        
            for mic_name in MIC_NAMES:
                
                mic = Device.objects.get(name=mic_name)
                mic_output = mic.outputs.all()[0]
                
                date = START_DATE
                
                while date <= END_DATE:
                                        
                    clip_pairs = pair_clips(
                        station, mic_output, date, detector_a, detector_b)
                    
                    write_diffs(
                        writer, station, mic_output, date, detector_a,
                        detector_b, clip_pairs)
                    
                    date += ONE_DAY
                    
    print(string.getvalue())
    
    
def pair_clips(station, mic_output, date, detector_a, detector_b):
    
    clips_a = get_clips(station, mic_output, date, detector_a)
    clips_b = get_clips(station, mic_output, date, detector_b)
    
    bounds_a = get_clip_bounds(clips_a)
    bounds_b = get_clip_bounds(clips_b)
    
    index_pairs = pair_clips_aux(bounds_a, bounds_b)
    
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

    
def pair_clips_aux(a, b):
    
    m = len(a)
    n = len(b)
    
    i = 0
    j = 0
    pairs = []

    while i < m:
        
        while j < n and b[j][1] <= a[i][0]:
            pairs.append((None, j))
            j += 1
            
        paired = False
        while j < n and b[j][0] <= a[i][1]:
            pairs.append((i, j))
            j += 1
            paired = True
            
        if not paired:
            pairs.append((i, None))
            
        i += 1
        
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


def write_diffs(
        writer, station, mic_output, date, detector_a, detector_b, clip_pairs):
    
    num_clips_a = 0
    num_clips_b = 0
    diffs_count = 0
    unpaired_count_a = 0
    unpaired_count_b = 0
    
    for pair in clip_pairs:
        
        clip_a, clip_b = pair
        
        if clip_a is not None and clip_b is not None and \
                (clip_a.start_index != clip_b.start_index or \
                 clip_a.length != clip_b.length):
#             a = get_clip_string(clip_a)
#             b = get_clip_string(clip_b)
#             print('    different {}  {}'.format(a, b))
            diffs_count += 1
            
        if clip_b is None:
#             a = get_clip_string(clip_a)
#             print('    unpaired a', a)
            unpaired_count_a += 1
        else:
            num_clips_b += 1
        
        if clip_a is None:
#             b = get_clip_string(clip_b)
#             print('    unpaired b', b)
            unpaired_count_b += 1
        else:
            num_clips_a += 1
            
    if num_clips_a != 0:
        diffs_percent = to_percent(diffs_count / num_clips_a)
        unpaired_percent_a = to_percent(unpaired_count_a / num_clips_a)
        unpaired_percent_b = to_percent(unpaired_count_b / num_clips_a)
    else:
        diffs_percent = 0
        unpaired_percent_a = 0
        unpaired_percent_b = 0
        
    writer.writerow(
        (station.name, mic_output.name, str(date),
         detector_a.name, detector_b.name,
         num_clips_a, num_clips_b,
         diffs_count, unpaired_count_a, unpaired_count_b,
         diffs_percent, unpaired_percent_a, unpaired_percent_b))
    
#     print('{} / {} / {} / {} / {}'.format(
#         station.name, mic_output.name, str(date),
#         detector_a.name, detector_b.name))
#                     
#     print(
#         '   ', num_clips_a, num_clips_b, ' ',
#         diffs_count, unpaired_count_a, unpaired_count_b, ' ',
#         diffs_percent, unpaired_percent_a, unpaired_percent_b)
   
    
def get_clip_string(c):
    return '({}, {}, {}, {:.3f})'.format(
        c.start_index, c.end_index, c.length, c.duration)


def to_percent(x):
    return round(1000 * x) / 10


def test_pair_clips_aux():
    
    cases = [
        
        # No clips.
        ([], [], []),
         
        # Paired, identical clips.
        ([(1, 2)], [(1, 2)], [(0, 0)]),
        ([(1, 2), (3, 4)], [(1, 2), (3, 4)], [(0, 0), (1, 1)]),
          
        # Paired, non-identical clips.
        ([(1, 2)], [(1, 3)], [(0, 0)]),
        ([(1, 2), (5, 6)], [(1, 3), (4, 6)], [(0, 0), (1, 1)]),
         
        # Unpaired clips.
        ([(1, 2)], [], [(0, None)]),
        ([], [(1, 2)], [(None, 0)]),
        ([(1, 2)], [(3, 4)], [(0, None), (None, 0)]),
        ([(1, 2), (7, 8)], [(3, 4), (5, 6)],
         [(0, None), (None, 0), (None, 1), (1, None)]),
         
        # Paired and unpaired clips.
        ([(1, 2), (3, 4), (7, 8)], [(3, 4), (5, 6), (7, 8)],
         [(0, None), (1, 0), (None, 1), (2, 2)])
        
    ]
    
    for a, b, expected in cases:
        result = pair_clips_aux(a, b)
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
