"""Populates a Vesper web app archive from an old desktop app archive."""


from collections import defaultdict
import datetime
import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from django.db import transaction

from vesper.archive.archive import Archive
from vesper.django.app.models import (
    AnnotationInfo, Clip, DeviceConnection, Recording, RecordingChannel,
    Station, StringAnnotation)
import vesper.django.app.model_utils as model_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


# TODO: Generalize this and package it as a Vesper importer that can be
# used in an import command.
#
# The importer requires that all stations, devices, processors, and
# annotations needed by the import are already present in the target
# archive.
#
# The import should be run in a transaction so that if any part of it
# fails the database can be rolled back to its state prior to the import.
#
# Command arguments will include:
#
# * The full path of the source archive directory, which must be on the server.
#
# * YAML describing:
#
#     * A mapping from source archive station names to target archive
#       (station name, microphone output name) pairs.
#
#     * A mapping from source archive detector names to target archive
#       detector names.
#
#     * Recording schedules, if needed. Recording schedules are needed
#       if and only if the source archive does not include recording
#       metadata.


_ARCHIVE_DIR_PATH = \
    r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch\MPG Ranch 2012-2014'
# _ARCHIVE_DIR_PATH = r'E:\2015_NFC_Archive'
# _ARCHIVE_DIR_PATH = r'E:\2016_archive'
# _ARCHIVE_DIR_PATH = \
#     r'C:\Users\Harold\Desktop\NFC\Data\Vesper-Example-Archive 0.1.0'

_DETECTOR_NAME_ALIASES = {
    'Old Bird Thrush': ['Thrush'],
    'Old Bird Tseep': ['Tseep']
}
# _DETECTOR_NAME_ALIASES = {
#     'Old Bird Tseep': ['Tseep']
# }

# Assumptions about station and microphone model names:
#
# * If a station name ends with one of the elements of _UNCORRECTED_MIC_NAMES,
#   the station name is a combination of a station name and an uncorrected
#   microphone model name.
#
# * If a station name does not end with one of the elements of
#   _UNCORRECTED_MIC_NAMES, the station name is just a plain station name
#   and the name of its microphone model is _DEFAULT_MIC_NAME.

_UNCORRECTED_MIC_NAMES = frozenset(['21c', 'NFC', 'SMX-II'])

_MIC_NAME_CORRECTIONS = {
    'NFC': 'SMX-NFC'
}

_DEFAULT_MIC_NAME = 'SMX-NFC'
# _DEFAULT_MIC_NAME = '21c'

_MIC_CHANNEL_NUMS = {
    'SMX-NFC': 0,
    '21c': 1
}


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
    
    channel_recordings = _get_channel_recordings()
    
    # Partition recording channels into sets that belong to the same
    # recording. The result is a mapping from (station, start_time)
    # pairs (with each pair representing a recording) to sets of
    # (recording_channel, mic_output) pairs.
    channel_info_sets = defaultdict(set)
    for r in channel_recordings:
        station, mic_output, recorder_input = \
            _get_recording_channel_info(r.station.name)
        channel_info_sets[(station, r.start_time)].add(
            (r, mic_output, recorder_input))
        
    keys = sorted(channel_info_sets.keys(), key=lambda p: (p[0].name, p[1]))
    
    for i, (station, start_time) in enumerate(keys):
        
        channel_infos = list(channel_info_sets[(station, start_time)])
        channel_infos.sort(key=lambda i: i[2].channel_num)
        
        r, _, recorder_input = channel_infos[0]
        recorder = recorder_input.device
        num_channels = len(channel_infos)
        span = (r.length - 1) / r.sample_rate
        end_time = r.start_time + datetime.timedelta(seconds=span)
        creation_time = time_utils.get_utc_now()
        recording = Recording(
            station=station,
            recorder=recorder,
            num_channels=num_channels,
            length=r.length,
            sample_rate=r.sample_rate,
            start_time=r.start_time,
            end_time=end_time,
            creation_time=creation_time,
            creating_job=None)
        recording.save()
        
        print('{} "{}" "{}"'.format(i, station.name, start_time))

        for _, mic_output, recorder_input in channel_infos:
            
            # We assume here that the recording channel number is the
            # same as the recorder channel number.
            channel_num = recorder_input.channel_num
            
            channel = RecordingChannel(
                recording=recording,
                channel_num=channel_num,
                recorder_channel_num=channel_num,
                mic_output=mic_output)  
            channel.save()
            
            print('    {} "{}"'.format(channel_num, mic_output.name))
        
        
def _get_channel_recordings():
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    channels = set()
    for station in stations:
        night = start_night
        while night <= end_night:
            for r in archive.get_recordings(station.name, night):
                channels.add(r)
            night += one_night
    archive.close()
    channels = list(channels)
    channels.sort(key=lambda r: (r.station.name, r.start_time))
    return channels


def _get_recording_channel_info(station_name):
    
    station_name, mic_name = _get_station_and_mic_name(station_name)
    
    station = Station.objects.get(name=station_name)
    
    mic = station.devices.get(
        model__type='Microphone',
        name__startswith=mic_name)
    
    # We assume here that each mic has exactly one output.
    mic_output = mic.outputs.all()[0]
    
    # We assume here that each mic output is connected to the same
    # channel of the same recorder throughout the archive.
    connection = DeviceConnection.objects.get(output=mic_output)
    recorder_input = connection.input
    
    return station, mic_output, recorder_input
    
    
def _get_station_and_mic_name(station_name):
    
    for mic_name in _UNCORRECTED_MIC_NAMES:
        if station_name.endswith(mic_name):
            station_name = station_name[:-(len(mic_name) + 1)]
            mic_name = _MIC_NAME_CORRECTIONS.get(mic_name, mic_name)
            return (station_name, mic_name)
            
    # If we get here, the station name does not end with any of the
    # elements of _UNCORRECTED_MIC_NAMES.
    return (station_name, _DEFAULT_MIC_NAME)

        
_clip_count = 0
_CLIP_COUNT_LIMIT = 1000000


def _add_clips():
    global _clip_count
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    detectors = _get_detectors()
    annotation_infos = _get_annotation_infos()
    num_added = 0
    num_rejected = 0
    for station in stations:
        night = start_night
        while night <= end_night:
            clips = archive.get_clips(station_name=station.name, night=night)
            (m, n) = _add_clips_aux(clips, night, detectors, annotation_infos)
            num_added += m
            num_rejected += n
            night += one_night
            if _clip_count >= _CLIP_COUNT_LIMIT:
                break
        if _clip_count >= _CLIP_COUNT_LIMIT:
            break
    archive.close()
    print('added {} clips, rejected {}'.format(num_added, num_rejected))
    
    
def _get_detectors():
    
    detectors = model_utils.get_processors('Detector')
    detectors = dict((d.name, d) for d in detectors)
    
    for name, aliases in _DETECTOR_NAME_ALIASES.items():
        detector = detectors[name]
        for alias in aliases:
            detectors[alias] = detector
            
    return detectors


def _get_annotation_infos():
    infos = AnnotationInfo.objects.all()
    return dict((i.name, i) for i in infos)


def _add_clips_aux(clips, night, detectors, annotation_infos):
    
    global _clip_count
    
    annotation_info = \
        _get_annotation_info('Classification', annotation_infos)
        
    num_added = 0
    num_rejected = 0
    
    for c in clips:
        
        try:
            channel = _get_clip_recording_channel(c)
        except Exception as e:
            print(str(e))
            num_rejected += 1
            continue
        
        try:
            detector = _get_detector(c, detectors)
        except ValueError as e:
            print(str(e))
            num_rejected += 1
            continue
        
        with transaction.atomic():
            
            recording = channel.recording
            channel_num = channel.channel_num
            station = recording.station
            mic_output = channel.mic_output
            length = audio_file_utils.get_wave_file_info(c.file_path).length
            start_time = c.start_time
            span = (length - 1) / recording.sample_rate
            end_time = start_time + datetime.timedelta(seconds=span)
            creation_time = time_utils.get_utc_now()
            
            clip = Clip(
                recording=recording,
                channel_num=channel_num,
                station=station,
                mic_output=mic_output,
                start_index=None,
                length=length,
                start_time=start_time,
                end_time=end_time,
                date=night,
                creation_time=creation_time,
                creating_processor=detector)
            print(_clip_count, clip)
            _clip_count += 1
            
            clip.save()
             
            _copy_clip_sound_file(c.file_path, clip)
            
            if c.clip_class_name is not None:
                value = StringAnnotation(
                    clip=clip,
                    info=annotation_info,
                    value=c.clip_class_name,
                    creation_time=creation_time)
                value.save()
            
            num_added += 1
        
    return (num_added, num_rejected)


def _get_clip_recording_channel(clip):
    station, _, recorder_input = _get_recording_channel_info(clip.station.name)
    return RecordingChannel.objects.get(
        recording__station=station,
        recording__recorder=recorder_input.device,
        recording__start_time__lte=clip.start_time,
        recording__end_time__gt=clip.start_time,
        channel_num=recorder_input.channel_num)
    
    
def _get_detector(clip, detectors):
    
    # TODO: Should manual clips be created by a particular user?
    
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
    
    
def _copy_clip_sound_file(file_path, clip):
    
    # TODO: Would it be significantly faster to copy files via the OS
    # rather than reading their contents and then writing them?
    
    with open(file_path, 'rb') as file_:
        contents = file_.read()
         
    # Create clip directory if needed.
    dir_path = os.path.dirname(clip.wav_file_path)
    os_utils.create_directory(dir_path)
    
    with open(clip.wav_file_path, 'wb') as file_:
        file_.write(contents)

    # print('Wrote file "{}" for clip {}.'.format(clip.wav_file_path, clip.id))

    
if __name__ == '__main__':
    _main()
    