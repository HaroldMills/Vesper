"""
Compares clips created by two detectors for a particular station, microphone,
and date.
"""


import datetime
import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.models import Clip, Device, Processor, Station


STATION_NAME = 'Floodplain'
MIC_NAME = '21c 0'
# MIC_NAME = 'SMX-NFC 2'
DATE = datetime.date(2016, 8, 25)
DETECTOR_NAME = 'Thrush'
SAMPLE_RATE = 22050


def main():
    
    station = Station.objects.get(name=STATION_NAME)
    
    mic = Device.objects.get(name=MIC_NAME)
    mic_output = mic.outputs.all()[0]

    detector_a_name = 'Old Bird {} Detector'.format(DETECTOR_NAME)
    detector_b_name = 'Old Bird {} Detector Redux 1.0'.format(DETECTOR_NAME)
    detector_a = Processor.objects.get(name=detector_a_name)
    detector_b = Processor.objects.get(name=detector_b_name)
        
    pair_clips(station, mic_output, DATE, detector_a, detector_b)
    
    # test_pair_clips()
    
    
def pair_clips(station, mic_output, date, detector_a, detector_b):
    
    clips_a = get_clips(station, mic_output, date, detector_a)
    clips_b = get_clips(station, mic_output, date, detector_b)
    
    pairs = pair_clips_aux(clips_a, clips_b)
    
    differences_count = 0
    extras_count_a = 0
    extras_count_b = 0
    
    for pair in pairs:
        
        clip_a, clip_b = pair
        
        if clip_a != clip_b:
            differences_count += 1
            
        if clip_a is None:
            extras_count_a += 1
        
        if clip_b is None:
            extras_count_b += 1
            
        if clip_a != clip_b:
            clip_a = add_duration(clip_a)
            clip_b = add_duration(clip_b)
            print(add_index(clip_a, clips_a))
            print(add_index(clip_b, clips_b))
            print()
            
    print(
        len(clips_a), len(clips_b), differences_count, extras_count_a,
        extras_count_b)
   
    
def get_clips(station, mic_output, date, detector):
    
    clips = [
        create_clip(c)
        for c in Clip.objects.filter(
            station=station,
            mic_output=mic_output,
            date=date,
            creating_processor=detector)]
    
    clips.sort(key=lambda c: c[0])
    
    return clips


def create_clip(c):
    return (c.start_index, c.start_index + c.length, str(c.start_time))


def pair_clips_aux(a, b):
    
    m = len(a)
    n = len(b)
    
    i = 0
    j = 0
    pairs = []

    while i < m:
        
        while j < n and b[j][1] <= a[i][0]:
            pairs.append((None, b[j]))
            j += 1
            
        paired = False
        while j < n and b[j][0] <= a[i][1]:
            pairs.append((a[i], b[j]))
            j += 1
            paired = True
            
        if not paired:
            pairs.append((a[i], None))
            
        i += 1
        
    while j < n:
        pairs.append((None, b[j]))
        j += 1
        
    return pairs
            
        
def add_duration(clip):
    if clip is None:
        return None
    else:
        duration = (clip[1] - clip[0]) / SAMPLE_RATE
        return clip + (duration,)
    
    
def add_index(clip, clips):
    if clip is None:
        return None
    else:
        for i, c in enumerate(clips):
            if clip[0] == c[0]:
                return (i + 1,) + clip
        
        
def test_pair_clips():
    
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
        result = pair_clips(a, b)
        expected = create_pairs(a, b, expected)
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
