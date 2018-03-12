"""Populates a Vesper web app archive from an old desktop app archive."""


from collections import defaultdict
import datetime
import os
import random
import time

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from django.db import transaction

from vesper.archive.archive import Archive
from vesper.django.app.models import (
    AnnotationInfo, Clip, DeviceConnection, Recording, RecordingChannel,
    Station)
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

_ARCHIVE_DIR_PATH = r'C:\Users\Harold\Desktop\2012 MPG Ranch Desktop Archive'
# _ARCHIVE_DIR_PATH = (
#     '/Users/Harold/Desktop/NFC/Data/MPG Ranch/2012 MPG Ranch Desktop Archive')
# _ARCHIVE_DIR_PATH = \
#     r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch\MPG Ranch 2012-2014'
# _ARCHIVE_DIR_PATH = r'E:\2015_NFC_Archive'
# _ARCHIVE_DIR_PATH = \
#     r'Y:\Desktop\NFC\Data\MPG Ranch\2016 MPG Ranch Desktop Archive'
# _ARCHIVE_DIR_PATH = \
#     '/Users/Harold/Desktop/NFC/Data/MPG Ranch/2016 MPG Ranch Desktop Archive'
# _ARCHIVE_DIR_PATH = r'F:\2016_archive'
# _ARCHIVE_DIR_PATH = \
#     r'C:\Users\Harold\Desktop\NFC\Data\Vesper-Example-Archive 0.1.0'

_CREATE_FAKE_RECORDINGS = False
"""Set `True` if and only if source archive does not contain recordings."""

_CLIP_COUNT_LIMIT = 100000000
"""The approximate maximum number of clips to process."""

_DETECTOR_NAME_ALIASES = {
    'Old Bird Thrush Detector': ['Thrush'],
    'Old Bird Tseep Detector': ['Tseep']
}
# _DETECTOR_NAME_ALIASES = {
#     'Old Bird Tseep Detector': ['Tseep']
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

_STATION_NAME_CORRECTIONS = {
    "St Mary's": 'St Mary'
}

_UNCORRECTED_MIC_NAMES = frozenset(['21c', 'NFC', 'SMX-II'])

_MIC_NAME_CORRECTIONS = {
    'NFC': 'SMX-NFC'
}

_DEFAULT_MIC_NAME = 'SMX-NFC'
# _DEFAULT_MIC_NAME = '21c'

_SHOW_RECORDINGS = False
_RECORDING_PROGRESS_PERIOD = 1000

_SHOW_CLIPS = False
_CLIP_PROGRESS_PERIOD = 10000
_NON_CALL_CLIP_INCLUSION_PROBABILITY = .11

_PAUSE_FILE_PATH = '/Users/Harold/Desktop/Pause'
_PAUSE_CHECK_PERIOD = 100
    
_ONE_NIGHT = datetime.timedelta(days=1)


def _main():
    random.seed(0)
    _delete_data()
    _add_data()
    

def _delete_data():
    for recording in Recording.objects.all():
        recording.delete()


def _add_data():
    _add_recordings()
    _add_clips()


def _add_recordings():
    
    processing_start_time = time.time()
    
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
    num_recordings = len(keys)
    
    for i, (station, start_time) in enumerate(keys):
        
        if i % _RECORDING_PROGRESS_PERIOD == 0:
            print('Recording {} of {}...'.format(i, num_recordings))
            
        channel_infos = list(channel_info_sets[(station, start_time)])
        channel_infos.sort(key=lambda i: i[2].channel_num)
        
        r, _, recorder_input = channel_infos[0]
        
        # Extend the length of the recording artificially by five seconds.
        # We do this because we have encountered cases where clips that
        # were extracted from recordings are stamped with times that are
        # up to a second past the end of the recording. We want to retain
        # all clips, however. In cases where we have the recordings from
        # which the clips were extracted, we can later find the precise
        # start indices of the clips in the recordings, and correct both
        # the clip start times and the recording durations in the archive.
        r.length += int(5 * r.sample_rate)
        
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
        
        if _SHOW_RECORDINGS:
            print('Recording {} {}'.format(i, str(recording)))

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
            
            if _SHOW_RECORDINGS:
                print('    Channel {} {}'.format(channel_num, mic_output.name))
        
    elapsed_time = time.time() - processing_start_time
    rate = num_recordings / elapsed_time
    
    print((
        'Processed {} recordings in {:.1f} seconds, an average of {:.1f} '
        'recordings per second.').format(len(keys), elapsed_time, rate))
        
        
def _get_channel_recordings():
    
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    
    stations = archive.stations
    
    start_night = archive.start_night
    end_night = archive.end_night
    
    channels = set()
    
    for station in stations:
        
        night = start_night
        
        while night <= end_night:
            
            for r in _get_night_channel_recordings(archive, station, night):
                channels.add(r)
                
            night += _ONE_NIGHT
            
    archive.close()
    
    channels = list(channels)
    channels.sort(key=lambda r: (r.station.name, r.start_time))
    
    return channels


def _get_night_channel_recordings(archive, station, night):
    if _CREATE_FAKE_RECORDINGS:
        return _create_fake_night_channel_recordings(archive, station, night)
    else:
        return archive.get_recordings(station.name, night)


_FAKE_RECORDING_START_HOUR = 19
_FAKE_RECORDING_DURATION = 12
_FAKE_RECORDING_SAMPLE_RATE = 22050
  
  
def _create_fake_night_channel_recordings(archive, station, night):
      
    from vesper.archive.recording import Recording as RecordingOld
      
    start_time = time_utils.create_utc_datetime(
        night.year, night.month, night.day, _FAKE_RECORDING_START_HOUR,
        time_zone=station.time_zone)
    
    length = \
        _FAKE_RECORDING_DURATION * 3600 * _FAKE_RECORDING_SAMPLE_RATE
        
    channel = RecordingOld(
        station, start_time, length, _FAKE_RECORDING_SAMPLE_RATE)
    
    return [channel]


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
            station_name = _correct(station_name, _STATION_NAME_CORRECTIONS)
            mic_name = _correct(mic_name, _MIC_NAME_CORRECTIONS)
            return (station_name, mic_name)
            
    # If we get here, the station name does not end with any of the
    # elements of _UNCORRECTED_MIC_NAMES.
    return (station_name, _DEFAULT_MIC_NAME)

        
def _correct(name, name_corrections):
    return name_corrections.get(name, name)


_clip_count = 0


def _add_clips():
    
    processing_start_time = time.time()
    
    global _clip_count
    
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    
    detectors = _get_detectors()
    annotation_infos = _get_annotation_infos()
    
    num_added = 0
    num_rejected = 0
    num_excluded = 0
    
    for station in stations:
        
        print('station "{}"...'.format(station.name))
        
        night = start_night
        
        while night <= end_night:
            
            clips = archive.get_clips(station_name=station.name, night=night)
            
            m, n, p = _add_clips_aux(clips, night, detectors, annotation_infos)
            
            num_added += m
            num_rejected += n
            num_excluded += p
            night += _ONE_NIGHT
            
            if _clip_count >= _CLIP_COUNT_LIMIT:
                break
            
        if _clip_count >= _CLIP_COUNT_LIMIT:
            break
        
    archive.close()
    
    num_clips = num_added + num_rejected + num_excluded
    elapsed_time = time.time() - processing_start_time
    rate = num_clips / elapsed_time
    
    print((
        'Processed {} clips in {:.1f} seconds, an average of {:.1f} '
        'clips per second.').format(num_clips, elapsed_time, rate))
    print('Added {} clips, rejected {}, excluded {}.'.format(
        num_added, num_rejected, num_excluded))
    
    
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
    num_excluded = 0
    
    for c in clips:
        
        _clip_count += 1
        
        if _clip_count % _CLIP_PROGRESS_PERIOD == 0:
            print('Clip {}...'.format(_clip_count))
            
        if _clip_count % _PAUSE_CHECK_PERIOD == 0:
            _pause_if_indicated()
            
        if not _include_clip(c):
            num_excluded += 1
            continue
        
        file_path = c.file_path
        
        if not (os.path.exists(file_path)):
            print(
                'Could not find clip file "{}". Clip will be ignored.'.format(
                    file_path))
            num_rejected += 1
            continue
        
        try:
            channel = _get_clip_recording_channel(c)
        except Exception:
            print((
                'Could not get recording channel for clip "{}". '
                'Clip will be ignored').format(file_path))
            num_rejected += 1
            continue
        
        try:
            detector = _get_detector(c, detectors)
        except ValueError:
            print((
                'Could not get detector "{}" for clip "{}". '
                'Clip will be ignored.').format(c.detector_name, file_path))
            num_rejected += 1
            continue
        
        with transaction.atomic():
            
            recording = channel.recording
            station = recording.station
            mic_output = channel.mic_output
            length = audio_file_utils.get_wave_file_info(file_path).length
            sample_rate = recording.sample_rate
            start_time = c.start_time
            span = (length - 1) / sample_rate
            end_time = start_time + datetime.timedelta(seconds=span)
            creation_time = time_utils.get_utc_now()
            
            clip = Clip(
                station=station,
                mic_output=mic_output,
                recording_channel=channel,
                start_index=None,
                length=length,
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time,
                date=night,
                creation_time=creation_time,
                creating_processor=detector)
            
            if _SHOW_CLIPS:
                print('Clip', _clip_count, clip)
                
            clip.save()
             
            _copy_clip_sound_file(file_path, clip)
            
            if c.clip_class_name is not None:
                
                # TODO: When this script becomes an importer, add the
                # creating job to the following.
                model_utils.annotate_clip(
                    clip, annotation_info, c.clip_class_name)
            
            num_added += 1
        
    return (num_added, num_rejected, num_excluded)


def _pause_if_indicated():
    
    if _pause_file_exists():
        print('pausing...')
        while True:
            time.sleep(1)
            if not _pause_file_exists():
                print('resuming...')
                break
            
            
def _pause_file_exists():
    return os.path.exists(_PAUSE_FILE_PATH)

                
def _include_clip(clip):
    
    return True

    name = clip.clip_class_name
    
    if name is None or name == 'Outside':
        return False
    
    elif name.startswith('Call'):
        return True
    
    else:
        return random.random() <= _NON_CALL_CLIP_INCLUSION_PROBABILITY
    
    
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
