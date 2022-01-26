from pathlib import Path
import datetime
import math
import time

import h5py

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import (
    AnnotationInfo, Clip, Processor, StringAnnotation)
from vesper.singleton.clip_manager import clip_manager
import vesper.django.app.model_utils as model_utils


# /Users/harold/Desktop/NFC/Data/MPG Ranch/2017 MPG Ranch Archive
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Part 1
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Part 2
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2019-07 Detector Development/Dataset Archives/Thrush/2017
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2019-07 Detector Development/Dataset Archives/Thrush/2018 Part 1
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2019-07 Detector Development/Dataset Archives/Thrush/2018 Part 2
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Detector Comparison/0.0/Part 1 Reduced
# /Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Detector Comparison/0.0/Part 2 Reduced


# ARCHIVE_NAME = '2017 MPG Ranch'
# ARCHIVE_NAME = '2018 MPG Ranch Part 1'
# ARCHIVE_NAME = '2018 MPG Ranch Part 2'
# ARCHIVE_NAME = '2018-08 MPG Ranch Noises'
ARCHIVE_NAME = '2018-09 MPG Ranch Noises'

OUTPUT_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'MPG Ranch Coarse Classifier 4.0/HDF5 Files/Thrush')

# DETECTOR_NAME = 'Old Bird Tseep Detector Redux 1.1'
# DETECTOR_NAME = 'MPG Ranch Tseep Detector 0.0 40'
# DETECTOR_NAME = 'Old Bird Thrush Detector Redux 1.1'
DETECTOR_NAME = 'MPG Ranch Thrush Detector 0.0 40'

ANNOTATION_NAME = 'Classification'

# ANNOTATION_VALUES = ['Call*', 'Noise', 'CHSP_DEJU', 'Tone']
# ANNOTATION_VALUES = ['Call*', 'Noise']
ANNOTATION_VALUES = ['Noise']

ANNOTATION_VALUE_WILDCARD = '*'

START_DATE = datetime.date(2018, 9, 1)
END_DATE = datetime.date(2018, 9, 30)

FILE_NAME_DETECTOR_INFO = {
    'Old Bird Tseep Detector Redux 1.1': ('Tseep', 'Old Bird Redux 1.1'),
    'Old Bird Thrush Detector Redux 1.1': ('Thrush', 'Old Bird Redux 1.1'),
    'MPG Ranch Tseep Detector 0.0 40': ('Tseep', 'MPG Ranch 0.0'),
    'MPG Ranch Thrush Detector 0.0 40': ('Thrush', 'MPG Ranch 0.0'),
}

EXTRACTION_START_OFFSETS = {
    'Old Bird Tseep Detector Redux 1.1': -.1,
    'Old Bird Thrush Detector Redux 1.1': -.05,
    'MPG Ranch Tseep Detector 0.0 40': -.05,
    'MPG Ranch Thrush Detector 0.0 40': -.05
}

EXTRACTION_DURATIONS = {
    'Old Bird Tseep Detector Redux 1.1': .5,
    'Old Bird Thrush Detector Redux 1.1': .65,
    'MPG Ranch Tseep Detector 0.0 40': .5,
    'MPG Ranch Thrush Detector 0.0 40': .65,
}

OTHER_ANNOTATION_NAMES = []

DEFAULT_ANNOTATION_VALUES = {}

START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def main():
    
    detector = Processor.objects.get(name=DETECTOR_NAME)
    # print(detector)
    
    annotation_info = AnnotationInfo.objects.get(name=ANNOTATION_NAME)
    # print(annotation_info)
    
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    
    for station, mic_output in sm_pairs:
        
        for annotation_value in ANNOTATION_VALUES:
            
            clips = get_clips(
                detector, station, mic_output, annotation_info,
                annotation_value)
            
            # Note that we ignore `mic_output` here: we assume that there
            # is only one mic output per station.
            create_hdf5_file(detector, station, annotation_value, clips)
            
    print('Done.')
    
    
def get_clips(
        detector, station, mic_output, annotation_info, annotation_value):
    
    clips = Clip.objects.filter(
        station=station,
        mic_output=mic_output,
        creating_processor=detector,
        date__gte=START_DATE,
        date__lte=END_DATE)

    clips = clips.filter(string_annotation__info=annotation_info)
    
    if not annotation_value.endswith(ANNOTATION_VALUE_WILDCARD):
        # want clips with a particular annotation value
        
        clips = clips.filter(string_annotation__value=annotation_value)
        
    elif annotation_value != ANNOTATION_VALUE_WILDCARD:
        # want clips whose annotation values start with a prefix
        
        prefix = annotation_value[:-len(ANNOTATION_VALUE_WILDCARD)]
        
        clips = clips.filter(string_annotation__value__startswith=prefix)
        
    clips = clips.order_by('start_time')
    
    return clips
        

def create_hdf5_file(detector, station, annotation_value, clips):
    
    detector_name = detector.name
    station_name = station.name
    
    file_name = create_file_name(detector_name, station_name, annotation_value)
    file_path = OUTPUT_DIR_PATH / file_name
    
    print('Writing clips to file "{}"...'.format(file_path))
    
    num_clips = clips.count()
    start_time = time.time()
    
    with h5py.File(file_path, 'w') as file_:
        
        extraction_start_offset = EXTRACTION_START_OFFSETS[detector_name]
        extraction_duration = EXTRACTION_DURATIONS[detector_name]
            
        _ = file_.create_group('/clips')
                
        num_unextracted_clips = 0
        
        for clip in clips:
            
            result = extract_samples(
                clip, extraction_start_offset, extraction_duration)
            
            if result is None:
                # extraction failed
                
                num_unextracted_clips += 1
            
            else:
                # extraction succeeded
                
                samples, start_index = result
                
                # Create dataset from clip samples.
                name = '/clips/{:08d}'.format(clip.id)
                file_[name] = samples
                
                # Set dataset attributes from clip metadata.
                attrs = file_[name].attrs
                attrs['clip_id'] = clip.id
                attrs['station'] = clip.station.name
                attrs['mic_output'] = clip.mic_output.name
                attrs['detector'] = clip.creating_processor.name
                attrs['date'] = str(clip.date)
                attrs['sample_rate'] = clip.sample_rate
                attrs['clip_start_time'] = format_datetime(clip.start_time)
                attrs['clip_start_index'] = clip.start_index
                attrs['clip_length'] = clip.length
                attrs['extraction_start_index'] = start_index
                
                annotations = get_annotations(clip)
                for name, value in annotations.items():
                    name = name.lower().replace(' ', '_')
                    attrs[name] = value
 
    elapsed_time = time.time() - start_time
    rate = num_clips / elapsed_time
    print((
        '    Processed {} clips in {:.1f} seconds, a rate of {:.1f} clips '
        'per second.').format(num_clips, elapsed_time, rate))
    
    if num_unextracted_clips != 0:
        if num_unextracted_clips == 1:
            text = 'one clip. That clip was'
        else:
            text = '{} clips. Those clips were'.format(num_unextracted_clips)
        print((
            '    Could not obtain samples for {} not written to the '
            'output file.').format(text))


def create_file_name(detector_name, station_name, annotation_value):
    
    detector_type, detector_name = FILE_NAME_DETECTOR_INFO[detector_name]
    
    if annotation_value.endswith(ANNOTATION_VALUE_WILDCARD):
        annotation_value = annotation_value[:-len(ANNOTATION_VALUE_WILDCARD)]
        
    # Replace '_' with '-' in annotation value since we use '_' to
    # separate file name components.
    annotation_value = annotation_value.replace('_', '-')
        
    return '{}_{}_{}_{}_{}.h5'.format(
        detector_type, ARCHIVE_NAME, detector_name, station_name,
        annotation_value)
    
    
def extract_samples(clip, extraction_start_offset, extraction_duration):
    
    sample_rate = clip.sample_rate
    
    start_offset = seconds_to_samples(
        extraction_start_offset, sample_rate)
    
    length = seconds_to_samples(extraction_duration, sample_rate)
    
    try:
        samples = clip_manager.get_samples(clip, start_offset, length)
    
    except Exception as e:
        print((
            'Could not get samples for clip {}, so it will not appear '
            'in output. Error message was: {}').format(str(clip), str(e)))
        return None
    
    start_index = clip.start_index + start_offset
    
    return samples, start_index


def seconds_to_samples(duration, sample_rate):
    sign = -1 if duration < 0 else 1
    return sign * int(math.ceil(abs(duration) * sample_rate))
    

def format_datetime(dt):
    return dt.strftime(START_TIME_FORMAT)


def get_annotations(clip):
    
    names = [ANNOTATION_NAME] + OTHER_ANNOTATION_NAMES
    
    return dict(
        [(name, get_annotation_value(clip, name)) for name in names])
            
            
def get_annotation_value(clip, annotation_name):
    
    try:
        annotation = clip.string_annotations.get(
            info__name=annotation_name)
        
    except StringAnnotation.DoesNotExist:
        return DEFAULT_ANNOTATION_VALUES.get(annotation_name)
    
    else:
        return annotation.value

            
if __name__ == '__main__':
    main()
