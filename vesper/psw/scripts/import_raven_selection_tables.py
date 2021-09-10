from datetime import datetime as DateTime, timedelta as TimeDelta
from pathlib import Path

from pytz import timezone

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from django.contrib.auth.models import User

from vesper.django.app.models import (
    AnnotationInfo, Clip, Processor, Recording, Station)
import vesper.django.app.model_utils as model_utils
import vesper.psw.util.raven_utils as raven_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


RECORDING_DIR_PATH = Path(
    '/Volumes/Recordings1/PSW/NOGO Archive 2 Recordings')

SELECTION_TABLE_FILE_NAME_SUFFIXES = ('_sel.NOGO.txt',)

TIME_ZONE = timezone('US/Pacific')

GROUND_TRUTH_DETECTOR_NAME = 'PSW Ground Truth NOGO Detector'

EXTRA_ANNOTATION_NAMES = (
    'Low Freq',
    'High Freq',
    'Detector',
    'Occupancy',
    'Notes',
    'Age',
    'Distance',
    'Noise'
)

SELECTION_TABLE_COLUMN_NAMES = {
    'Low Freq': 'Low Freq (Hz)',
    'High Freq': 'High Freq (Hz)'
}

NO_VALUE = ''

CLIP_PADDING = .100


def main():
    for file_path in RECORDING_DIR_PATH.glob('*'):
        if raven_utils.is_selection_table_file_name(
                file_path.name, SELECTION_TABLE_FILE_NAME_SUFFIXES):
            import_selections(file_path)
    
    
def import_selections(file_path):
    
    print(f'Importing Raven selections from file "{file_path}"...')
    
    station_name, recording_start_time = \
        parse_selection_table_file_name(file_path.name)
        
    header, rows = raven_utils.read_selection_table_file(file_path)
    
    create_clips(station_name, recording_start_time, header, rows)
    
    
def parse_selection_table_file_name(name):
    station_name, date, time = name.split('_')[:3]
    year = int(date[:4])
    month = int(date[4:6])
    day = int(date[6:8])
    hour = int(time[:2])
    minute = int(time[2:4])
    second = int(time[4:6])
    local_start_time = DateTime(year, month, day, hour, minute, second)
    utc_start_time = TIME_ZONE.localize(local_start_time)
    return station_name, utc_start_time
    
    
'''
Assumptions:

* Each recording has one channel.

* Each station has one microphone with one output.

* Each station has one recorder with one input.

* The microphone output is connected to the recorder input.

Starting with a station name and a recording start time, we do:

* station name -> station
* station -> station devices
* station devices -> mic, recorder
* station, recorder, start time -> recording
* mic -> mic output
* recording, mic output -> recording channel

From the station, mic output, and recording channel we can then create a clip.
'''


'''
Truth dataset classifications:

Douglas Squirrel.call    2
Duplicate    108
NOGO    228
NOGO.call    6
NOGO.call.dismissal    9
NOGO.call.guck    2
NOGO.call.terp    8
NOGO.kek.series    3
NOGO.kek.single    3
NOGO.kek.soft    8
NOGO.kek.soft kek    1
NOGO.wail    72
NOGO.wail.broken    6
NOGO.wail.dismissal    35
NOGO.wail.kree-ah    2
NOGO.wail.upslur    1
NOGO.wail.whai-ae    8
'''


def create_clips(station_name, recording_start_time, header, rows):
    
    station = Station.objects.get(name=station_name)
    
    # Here we assume that each station has exactly one mic.
    mic = get_station_device(station, 'Microphone')
    
    # Here we assume that the mic has exactly one output.
    mic_output = mic.outputs.get()
    
    # Here we assume that each station has exactly one recorder.
    recorder = get_station_device(station, 'Audio Recorder')
    
    try:
        recording = Recording.objects.get(
            station=station, recorder=recorder, start_time=recording_start_time)
    except Exception:
        print(
            f'Could not get recording for station "{station}", '
            f'recorder "{recorder}", and start time {recording_start_time}.')
        raise
    
    # Here we assume that each recording has exactly one channel.
    recording_channel = recording.channels.get()
    
    sample_rate = recording.sample_rate
    
    creation_time = time_utils.get_utc_now()
    creating_detector = Processor.objects.get(name=GROUND_TRUTH_DETECTOR_NAME)
    creating_user = User.objects.get(username='Lief')
    
    annotation_names = ('Classification',) + EXTRA_ANNOTATION_NAMES
    annotation_infos = dict(
        (name, AnnotationInfo.objects.get(name=name))
        for name in annotation_names)
    
    for row in rows:
        create_clip(
            station, mic_output, recording_channel, recording_start_time,
            sample_rate, creation_time, creating_detector,
            creating_user, annotation_infos, header, row)
        
        
def get_station_device(station, device_type):
    return station.devices.get(model__type=device_type)


def create_clip(
        station, mic_output, recording_channel, recording_start_time,
        sample_rate, creation_time, creating_detector, creating_user,
        annotation_infos, header, row):
    
    cells = dict(zip(header, row))
    
    # Get clip start and end UTC times.
    start_offset = float(cells['Begin Time (s)']) - CLIP_PADDING
    start_time = get_time(recording_start_time, start_offset)
    end_offset = float(cells['End Time (s)']) + CLIP_PADDING
    end_time = get_time(recording_start_time, end_offset)
    
    # Get clip start index and length.
    s2f = signal_utils.seconds_to_frames
    start_index = s2f(start_offset, sample_rate)
    duration = (end_time - start_time).total_seconds()
    length = s2f(duration, sample_rate)
    
    date = station.get_night(start_time)
    
    clip = Clip(
        station=station,
        mic_output= mic_output,
        recording_channel=recording_channel,
        start_index=start_index,
        length=length,
        sample_rate=sample_rate,
        start_time=start_time,
        end_time=end_time,
        date=date,
        creation_time=creation_time,
        creating_processor=creating_detector)
    
    clip.save()

    for annotation_name in EXTRA_ANNOTATION_NAMES:
        
        column_name = SELECTION_TABLE_COLUMN_NAMES.get(
            annotation_name, annotation_name)
        
        annotation_value = cells.get(column_name)
        
        annotate_clip(
            clip, annotation_name, annotation_value, annotation_infos,
            creation_time, creating_user)
        
    classification = get_classification(cells)
                
    annotate_clip(
        clip, 'Classification', classification, annotation_infos,
        creation_time, creating_user)
    
    
def get_time(time, offset):
    offset = TimeDelta(seconds=offset)
    return time + offset


def annotate_clip(
        clip, annotation_name, annotation_value, annotation_infos,
        creation_time, creating_user):
    
    if annotation_value is not None:
        
        annotation_info = annotation_infos[annotation_name]
    
        model_utils.annotate_clip(
            clip,
            annotation_info=annotation_info,
            value=annotation_value,
            creation_time=creation_time,
            creating_user=creating_user)
        

def get_classification(cells):
    
    classification = cells.get('Species')
    
    if classification != NO_VALUE:
        
        vocalization_type = cells.get('VocType')
        
        if vocalization_type != NO_VALUE:
            
            classification += '.' + vocalization_type
            
            vocalization_subtype = cells.get('SubType')
            
            if vocalization_subtype != NO_VALUE:
                
                classification += '.' + vocalization_subtype
                
    return classification


if __name__ == '__main__':
    main()
