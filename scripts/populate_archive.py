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
    Annotation, Clip, Device, DeviceModel, Recording, Station)
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


_ARCHIVE_DIR_PATH = \
    r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch\MPG Ranch 2012-2014'
_ARCHIVE_DATABASE_FILE_NAME = 'Archive Database.sqlite'
_ARCHIVE_DATABASE_FILE_PATH = os.path.join(
    _ARCHIVE_DIR_PATH, _ARCHIVE_DATABASE_FILE_NAME)


def _main():
    _delete_data()
    _add_data()
    # _show_data()
    

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
        recording = Recording(
            station_recorder=station_recorder, num_channels=1, length=r.length,
            sample_rate=r.sample_rate, start_time=r.start_time,
            end_time=end_time)
        recording.save()
        
    
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
    num_added = 0
    num_rejected = 0
    for station in stations:
        night = start_night
        while night <= end_night:
            clips = archive.get_clips(station_name=station.name, night=night)
            (m, n) = _add_clips_aux(clips, station_recordings)
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
        
        
def _add_clips_aux(clips, station_recordings):
    
    num_added = 0
    num_rejected = 0
    
    for c in clips:
        
        try:
            recording = _get_clip_recording(c, station_recordings)
        except ValueError as e:
            print(str(e))
            num_rejected += 1
            continue
        
        with transaction.atomic():
            
            length = audio_file_utils.get_wave_file_info(c.file_path)[3]
            start_time = c.start_time
            span = (length - 1) / recording.sample_rate
            end_time = start_time + datetime.timedelta(seconds=span)
            creation_time = time_utils.get_utc_now()
            
            # TODO: Include creating processor (i.e. detector).
            clip = Clip(
                recording=recording, channel_num=0, start_index=None,
                length=length, start_time=start_time, end_time=end_time,
                creation_time=creation_time)
            clip.save()
            
            _copy_clip_sound_file(c.file_path, clip)
            
            a = Annotation(clip=clip, name='Detector', value=c.detector_name)
            a.save()
            
            s = c.selection
            if s is not None:
                a = Annotation(
                    clip=clip, name='Selection Start Index', value=s[0])
                a.save()
                a = Annotation(clip=clip, name='Selection Length', value=s[1])
                a.save()
            
            a = Annotation(
                clip=clip, name='Classification', value=c.clip_class_name)
            a.save()
            
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


def _show_data():
    _show_device_models()
    print()
    _show_devices()
    print()
    _show_stations()
    print()
    _show_recordings()
    print()
    _show_clips()
    
    
def _show_device_models():
    for model in DeviceModel.objects.all():
        print(model)
        for input_ in model.inputs.all():
            print('    ' + str(input_))
        for output in model.outputs.all():
            print('    ' + str(output))
            
            
def _show_devices():
    for device in Device.objects.all():
        print(device)
        for input_ in device.inputs.all():
            print('    ' + str(input_))
        for output in device.outputs.all():
            print('    ' + str(output))
            
            
def _show_stations():
    for station in Station.objects.all():
        print(station)
        for sd in station.device_associations.all():
            print('    ', sd)
            for output in sd.device.outputs.all():
                for connection in output.connections.filter(
                        start_time__range=(sd.start_time, sd.end_time)):
                    print('        ', connection)
    

def _show_recordings():
    for recording in Recording.objects.all():
        print(recording)
        
        
def _show_clips():
    for clip in Clip.objects.all():
        annotations = Annotation.objects.filter(clip=clip)
        detector = annotations.get(name='Detector').value
        try:
            selection_start_index = \
                annotations.get(name='Selection Start Index').value
        except Annotation.DoesNotExist:
            selection_start_index = None
            selection_length = None
        else:
            selection_length = annotations.get(name='Selection Length').value
        classification = annotations.get(name='Classification').value
        print('{} {} {} {} {}'.format(
            str(clip), detector, selection_start_index, selection_length,
            classification))
        
        
if __name__ == '__main__':
    _main()
    