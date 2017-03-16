"""Populates a Vesper web app archive from an old desktop app archive."""


from collections import defaultdict
import datetime
import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from django.db import transaction
import pytz

from vesper.archive.archive import Archive
from vesper.django.app.models import (
    AnnotationInfo, Clip, Processor, Recording, Station, StringAnnotation)
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


_ARCHIVE_DIR_PATH = \
    r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch\MPG Ranch 2012-2014'
# _ARCHIVE_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\Vesper-Example-Archive'

_DETECTOR_NAME_ALIASES = {
    'Old Bird Thrush': ['Thrush'],
    'Old Bird Tseep': ['Tseep']
}
# _DETECTOR_NAME_ALIASES = {
#     'Old Bird Tseep': ['Tseep']
# }


def _main():
    _delete_data()
    _add_data()
    

def _delete_data():
    for recording in Recording.objects.all():
        recording.delete()


def _add_data():
    _add_recordings()
    _add_clips()


def _add_recordings():
    recordings = _get_recordings()
    for r in recordings:
        station_recorder = _get_recording_station_recorder(r)
        span = (r.length - 1) / r.sample_rate
        end_time = r.start_time + datetime.timedelta(seconds=span)
        creation_time = time_utils.get_utc_now()
        recording = Recording(
            station_recorder=station_recorder,
            num_channels=1,
            length=r.length,
            sample_rate=r.sample_rate,
            start_time=r.start_time,
            end_time=end_time,
            creation_time=creation_time,
            creating_job=None)
        recording.save()
        
    
# _FAKE_RECORDING_START_HOUR = 19
# _FAKE_RECORDING_DURATION = 12
# _FAKE_RECORDING_SAMPLE_RATE = 22050
#  
#  
# def _get_recordings():
#      
#     from vesper.archive.recording import Recording as RecordingOld
#      
#     archive = Archive(_ARCHIVE_DIR_PATH)
#     archive.open()
#     stations = archive.stations
#     start_night = archive.start_night
#     end_night = archive.end_night
#     one_night = datetime.timedelta(days=1)
#     recordings = set()
#     for station in stations:
#         night = start_night
#         while night <= end_night:
#             start_time = time_utils.create_utc_datetime(
#                 night.year, night.month, night.day, _FAKE_RECORDING_START_HOUR,
#                 time_zone=station.time_zone)
#             length = \
#                 _FAKE_RECORDING_DURATION * 3600 * _FAKE_RECORDING_SAMPLE_RATE
#             recording = RecordingOld(
#                 station, start_time, length, _FAKE_RECORDING_SAMPLE_RATE)
#             recordings.add(recording)
#             night += one_night
#     archive.close()
#     recordings = list(recordings)
#     recordings.sort(key=lambda r: (r.station.name, r.start_time))
#     return recordings


def _get_recordings():
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    recordings = set()
    for station in stations:
        night = start_night
        while night <= end_night:
            for r in archive.get_recordings(station.name, night):
                recordings.add(r)
            night += one_night
    archive.close()
    recordings = list(recordings)
    recordings.sort(key=lambda r: (r.station.name, r.start_time))
    return recordings


def _get_recording_station_recorder(recording):
    
    station = Station.objects.get(name=recording.station.name)
    start_time = recording.start_time
    end_time = recording.end_time
    
    station_recorders = \
        station.get_station_devices('Audio Recorder', start_time, end_time)
        
    if len(station_recorders) == 0:
        raise ValueError(
            'Could not find recorder for station "{}".'.format(station.name))
    
    elif len(station_recorders) > 1:
        raise ValueError(
            'Found more than one recorder for station "{}".'.format(
                station.name))
        
    else:
        return station_recorders[0]
    

def _add_clips():
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    station_recordings = _get_station_recordings()
    detectors = _get_detectors()
    annotation_infos = _get_annotation_infos()
    num_added = 0
    num_rejected = 0
    for station in stations:
        night = start_night
        while night <= end_night:
            clips = archive.get_clips(station_name=station.name, night=night)
            (m, n) = _add_clips_aux(
                clips, station_recordings, detectors, annotation_infos)
            num_added += m
            num_rejected += n
            night += one_night
    archive.close()
    print('added {} clips, rejected {}'.format(num_added, num_rejected))
    
    
def _get_station_recordings():
    recordings = defaultdict(list)
    for recording in Recording.objects.all():
        recordings[recording.station.name].append(recording)
    return recordings
        
        
def _get_detectors():
    
    detectors = Processor.objects.filter(
        algorithm_version__algorithm__type='Detector')
    
    detectors = dict((d.name, d) for d in detectors)
    
    for name, aliases in _DETECTOR_NAME_ALIASES.items():
        detector = Processor.objects.get(name=name)
        for alias in aliases:
            detectors[alias] = detector
            
    return detectors


def _get_annotation_infos():
    infos = AnnotationInfo.objects.all()
    return dict((i.name, i) for i in infos)


def _add_clips_aux(clips, station_recordings, detectors, annotation_infos):
    
    num_added = 0
    num_rejected = 0
    
    for c in clips:
        
        try:
            recording = _get_clip_recording(c, station_recordings)
        except ValueError as e:
            print(str(e))
            num_rejected += 1
            continue
        
        try:
            detector = _get_detector(c, detectors)
        except ValueError as e:
            print(str(e))
            num_rejected += 1
            continue
        
        annotation_info = \
            _get_annotation_info('Classification', annotation_infos)
        
        with transaction.atomic():
            
            length = audio_file_utils.get_wave_file_info(c.file_path).length
            start_time = c.start_time
            span = (length - 1) / recording.sample_rate
            end_time = start_time + datetime.timedelta(seconds=span)
            creation_time = time_utils.get_utc_now()
            
            clip = Clip(
                recording=recording,
                channel_num=0,
                start_index=None,
                length=length,
                start_time=start_time,
                end_time=end_time,
                creation_time=creation_time,
                creating_processor=detector)
            clip.save()
            
            _copy_clip_sound_file(c.file_path, clip)
            
            value = StringAnnotation(
                clip=clip, info=annotation_info, value=c.clip_class_name,
                creation_time=creation_time)
            value.save()
            
            num_added += 1
        
    return (num_added, num_rejected)
    

def _copy_clip_sound_file(file_path, clip):
    
    with open(file_path, 'rb') as file_:
        contents = file_.read()
         
    # Create clip directory if needed.
    dir_path = os.path.dirname(clip.wav_file_path)
    os_utils.create_directory(dir_path)
    
    with open(clip.wav_file_path, 'wb') as file_:
        file_.write(contents)

    print('Wrote file "{}" for clip {}.'.format(clip.wav_file_path, clip.id))

    
def _get_clip_recording(clip, station_recordings):
    
    time = clip.start_time
    
    # Django doesn't seem to support this. Not sure why.
    # Update: I made a mistake by specifying `start_time__le` rather than
    # `start_time__lte` and `end_time__ge` rather than `end_time__gte`.
    # That's why my code didn't work!
#     try:
#         return station.recordings.get(start_time__le=time, end_time__ge=time)
#     except Recording.DoesNotExist:
#         raise ValueError(
#             'Could not find recording for clip "{}".'.format(clip.file_path))

    # TODO: Sort recordings by start time and use binary search to
    # find the recording that contains a clip.
    for r in station_recordings[clip.station.name]:
        start_time = r.start_time
        end_time = r.end_time
        if start_time <= time and time <= end_time:
            return r
    raise ValueError(
        'Could not find recording for clip "{}".'.format(clip.file_path))
    
    
def _get_detector(clip, detectors):
    
    if clip.detector_name == 'Manual':
        return None
    
    else:
        
        try:
            return detectors[clip.detector_name]
        except KeyError:
            raise ValueError(
                'Unrecognized detector "{}".'.format(clip.detector_name))
        
        
def _get_annotation_info(name, annotation_infos):
    try:
        return annotation_infos[name]
    except KeyError:
        raise ValueError('Unrecognized annotation "{}".'.format(name))
    
    
def _get_floor_noon(time, station):
    time_zone = pytz.timezone(station.time_zone)
    dt = time.astimezone(time_zone)
    d = dt.date()
    if dt.hour < 12:
        d -= datetime.timedelta(days=1)
    noon = datetime.datetime(d.year, d.month, d.day, 12)
    noon = time_zone.localize(noon)
    noon = noon.astimezone(pytz.utc)
    return noon


if __name__ == '__main__':
    _main()
    