"""Module containing class `ClipImporter`."""


import datetime
import logging
import os.path
import re
import time


from pathlib import Path

from django.db import transaction

from vesper.django.app.models import (
    AnnotationInfo, Clip, Job, Processor, Recording, RecordingChannel, Station,
    StationDevice)
from vesper.singleton.clip_manager import clip_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.file_type_utils as file_type_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils


_DETECTOR_NAMES = {
    'Tseep': 'Old Bird Tseep Detector',
    'Thrush': 'Old Bird Thrush Detector'
}

_RECORDING_DATA = {
    
#     'CLC': [
#         
#         {
#             'start_date': datetime.date(2017, 1, 1),
#             'end_date': datetime.date(2018, 1, 1),
#             'start_time': datetime.time(21),
#             'end_time': datetime.time(5)
#         }
#     ],
#                    
#     'JAS': [
#         {
#             'start_date': datetime.date(2017, 1, 1),
#             'end_date': datetime.date(2018, 1, 1),
#             'start_time': datetime.time(20, 30),
#             'end_time': datetime.time(5, 30)
#         }
#     ],
                   
    'Deline': [
        {
            'start_date': datetime.date(2006, 1, 1),
            'end_date': datetime.date(2007, 1, 1),
            'start_time': datetime.time(12, 0, 0),
            'end_time': datetime.time(11, 59, 59)
        }
    ]
                   
}

# _CLASSIFICATION_ALIASES = {
#     'Call': ['calls'],
#     'Tone': ['tones']
# }

# Deline
_CLASSIFICATION_ALIASES = {
    'Call': [
        'call', 'calls', 'calls2', 'warblers and sparrows', 'first set',
        'second set', 'third set', 'fourth set', 'fifth set', 'six set',
        'sixth set', 'seventh set', 'eighth set', 'ninth set', 'tenth set'],
    'Call.CORE': ['common redpoll'],
    'Call.GCTH': ['gray-cheeked thrush'],
    'Call.Gull': ['gulls'],
    'Call.HETH': ['hermit thrush'],
    'Call.Interesting': ['interesting unid', 'interesting unided calls'],
    'Call.Local WCSP': ['white-crowned sparrows local on ground'],
    'Call.Longspur?': ['possible longspur'],
    'Call.Pipit?': ['are these pipit'],
    'Call.Shorebird': ['shorebird', 'shorebirds'],
    'Call.Sparrow': ['sparrow', 'sparrows'],
    'Call.SWTH': ['swainsons thrush'],
    'Call.Thrush': ['thrush', 'thrushes'],
    'Call.Tseep': ['tseep', 'tseeps'],
    'Call.Uninteresting': [
        'not very interesting', 'uninteresting-local', 'uninteresting local'],
    'Call.Warbler': ['warbler', 'warblers'],
    'Call.WRSA?': ['possible white-rumped sandpiper'],
    'Noise': ['noise', 'noises'],
    'Red Squirrel': ['red squirrel', 'red squirrels']
}

_NUM_RECORDING_CHANNELS = 1
_RECORDING_CHANNEL_NUM = 0
_RECORDER_CHANNEL_NUM = 0

_ANNOTATION_NAME = 'Classification'

_ONE_DAY = datetime.timedelta(days=1)


class _ImportError(Exception):
    pass


class ClipImporter:
    
    """Importer for Old Bird clips."""
    
    
    extension_name = 'Old Bird Clip Importer'
    
    
    def __init__(self, args):
        get = command_utils.get_required_arg
        self.paths = get('paths', args)
        self.start_date = get('start_date', args)
        self.end_date = get('end_date', args)
        
    
    def execute(self, job_info):
        
        self._logger = logging.getLogger()
        
        self._job = Job.objects.get(id=job_info.job_id)
        
        self._stations = self._get_stations()
        self._detectors = self._get_detectors()
        self._recorders = self._get_recorders()
        self._mic_outputs = self._get_mic_outputs()
        self._recording_channels = self._get_recording_channels()
        self._annotation_info = self._get_annotation_info()
        
        self._classifications = self._get_classifications()
        
        self._logger.info('Beginning import...')
        
        start_time = time.time()
        
        self._file_count = 0
        self._parsed_count = 0
        self._eligible_count = 0
        self._imported_count = 0
        
        for path in self.paths:
            self._import_clips(path)
            
        elapsed_time = time.time() - start_time
        
        self._log_summary(elapsed_time)
        
        return True


    def _log_summary(self, elapsed_time):
        
        create_units_text = text_utils.create_units_text
        log = self._logger.info
        
        # Number of audio files processed.
        units = create_units_text(self._file_count, 'audio file')
        timing_text = command_utils.get_timing_text(
            elapsed_time, self._file_count, 'files')
        log('Processed {} {}{}.'.format(self._file_count, units, timing_text))
        
        # Number of file path parse errors.
        count = self._file_count - self._parsed_count
        if count != 0:
            units = create_units_text(count, 'audio file path')
            log(('{} {} could not be parsed. See error messages above '
                 'for details.').format(count, units))
        
        # Number of excluded files.
        count = self._parsed_count - self._eligible_count
        if count != 0:
            units = create_units_text(
                count, 'audio file was', 'audio files were')
            log('{} {} excluded by date.'.format(count, units))
            
        # Number of failed imports.
        count = self._eligible_count - self._imported_count
        if count != 0:
            units = create_units_text(count, 'attempted clip import')
            log('{} {} failed. See error messages above for details.'.format(
                count, units))
            
        # Number of successful imports.
        units = create_units_text(self._imported_count, 'clip')
        log('{} {} were imported.'.format(self._imported_count, units))
        
        
    def _get_stations(self):
        return dict([(s.name, s) for s in Station.objects.all()])
    
    
    def _get_detectors(self):
        return dict(
            [(d.name, d) for d in Processor.objects.filter(type='Detector')])
        
        
    def _get_mic_outputs(self):
        
        '''
        We assume that every station has exactly one microphone and
        that every microphone has exactly one output.
        '''
        
        return dict([
            (sd.station.name, sd.device.outputs.first())
            for sd in StationDevice.objects.filter(
                device__model__type='Microphone')])
            
            
    def _get_recorders(self):
        
        '''We assume that every station has exactly one recorder.'''
        
        return dict([
            (sd.station.name, sd.device)
            for sd in StationDevice.objects.filter(
                device__model__type='Audio Recorder')])
        
        
    def _get_recording_channels(self):
        
        '''
        We assume that every recording has one channel, and that there
        is at most one recording per station per night.
        '''
        
        return dict([
            (_get_recording_channels_key(rc), rc)
            for rc in RecordingChannel.objects.all()])
        
        
    def _get_annotation_info(self):
        
        try:
            return AnnotationInfo.objects.get(name=_ANNOTATION_NAME)
                
        except AnnotationInfo.DoesNotExist:
            raise ValueError(
                'Could not find information for annotation "{}".'.format(
                    _ANNOTATION_NAME))
            
            
    def _get_classifications(self):
        classifications = {}
        for classification, aliases in _CLASSIFICATION_ALIASES.items():
            classifications[classification.lower()] = classification
            for alias in aliases:
                classifications[alias.lower()] = classification
        return classifications
                
            
    def _import_clips(self, path):
        
        for (dir_path, _, file_names) in os.walk(path):
            
            self._logger.info(
                'Importing clips from directory "{}"...'.format(dir_path))
            
            for file_name in file_names:
                
                file_path = os.path.join(dir_path, file_name)
                
                if file_type_utils.is_wave_file(Path(file_path)):
                    self._process_audio_file(file_path)
                    self._file_count += 1
                    
                    
    def _process_audio_file(self, file_path):
        
        try:
            info = self._parse_file_path(file_path)
           
        except Exception as e:
            self._logger.error(
                'Parse failed for clip file path "{}" with message: {}'.format(
                    file_path, str(e)))
            return
            
        self._parsed_count += 1
       
        if self.start_date is not None and info.date < self.start_date or \
                self.end_date is not None and info.date > self.end_date:
            # not importing clips for this date
            
            return
        
        self._eligible_count += 1
        
        try:
            self._import_clip(file_path, info)
           
        except Exception as e:
            self._logger.error(
                'Clip import failed for file "{}" with message: {}'.format(
                    file_path, str(e)))
            return
           
        self._imported_count += 1
        
           
    def _parse_file_path(self, file_path):
        
        parts = Path(file_path).parts
        file_name = parts[-1]
        dir_names = tuple(reversed(parts[:-1]))
        
        # Get classification from file parent dir name if name indicates it.
        key = dir_names[0].lower()
        classification = self._classifications.get(key)
        
        if classification is None:
            self._logger.warning((
                'Could not find classification for file "{}". Clip will '
                'be unclassified.').format(
                    file_path))
        else:
            dir_names = dir_names[1:]
            
        station = self._get_station(dir_names)
        
        # Get clip detector, start time, and date.
        detector_name, local_start_time = _parse_file_name(file_name)
        detector = self._get_detector(detector_name)
        start_time = station.local_to_utc(local_start_time)
        date = station.get_night(start_time)
        
        return Bunch(
            station=station,
            detector=detector,
            start_time=start_time,
            date=date,
            classification=classification)
        
        
    @transaction.atomic
    def _import_clip(self, file_path, info):
        
        length, sample_rate = _get_audio_file_info(file_path)
        
        start_time = info.start_time
        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
        
        mic_output = self._get_mic_output(info.station.name)
        recording_channel = self._get_recording_channel(
            info.station, info.date, sample_rate)
        
        recording = recording_channel.recording
        _assert_recording_contains_clip(recording, start_time, end_time)

        creation_time = time_utils.get_utc_now()
        
        clip = Clip.objects.create(
            station=info.station,
            mic_output=mic_output,
            recording_channel=recording_channel,
            start_index=None,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            date=info.date,
            creation_time=creation_time,
            creating_job=self._job,
            creating_processor=info.detector)

        _copy_clip_audio_file(file_path, clip)
        
        if info.classification is not None:
            
            creation_time = time_utils.get_utc_now()
            
            # We assume that any classification performed before the
            # import was by the user who started the import.
            creating_user = self._job.creating_user
            
            model_utils.annotate_clip(
                clip, self._annotation_info, info.classification,
                creation_time=creation_time, creating_user=creating_user)
            
            
    def _get_station(self, dir_names):
        
        for dir_name in dir_names:
            station = self._stations.get(dir_name)
            if station is not None:
                return station
            
        # If we get here, no directory name was a station name.
        raise ValueError(
            'Could not find a station name among ancestor directory names.')
        
        
    def _get_detector(self, name):
    
        try:
            name = _DETECTOR_NAMES[name]
        except KeyError:
            raise ValueError(
                'Unrecognized detector name "{}".'.format(name))
            
        try:
            return self._detectors[name]
        except KeyError:
            raise ValueError(
                'Unrecognized detector name "{}".'.format(name))
            
            
    def _get_mic_output(self, station_name):
        
        try:
            return self._mic_outputs[station_name]
        except KeyError:
            raise ValueError(
                'Could not find microphone output for station "{}".'.format(
                    station_name))
            
         
    def _get_recorder(self, station_name):
        
        try:
            return self._recorders[station_name]
        except KeyError:
            raise ValueError(
                'Could not find recorder for station "{}".'.format(
                    station_name))


    def _get_recording_channel(self, station, date, sample_rate):
        
        key = (station.name, date)
        
        try:
            rc = self._recording_channels[key]
        
        except KeyError:
            # no recording yet for this station and date
            
            # Create new recording channel and cache it..
            rc = self._create_recording_channel(station, date, sample_rate)
            self._recording_channels[key] = rc
            
        return rc
        
        
    def _create_recording_channel(self, station, date, sample_rate):
        
        station_name = station.name
        recorder = self._get_recorder(station_name)
        mic_output = self._get_mic_output(station_name)
        
        start_time, end_time = \
            _get_recording_start_and_end_times(station, date)
        
        duration = (end_time - start_time).total_seconds()
        length = int(round(duration * sample_rate))

        # Recompute end time from recording start time, length, and
        # sample rate so it is consistent with our definition (i.e. so
        # that it is the time of the last sample of the recording rather
        # than the time of the sample after that).
        end_time = signal_utils.get_end_time(start_time, length, sample_rate)

        creation_time = time_utils.get_utc_now()
        
        recording = Recording.objects.create(
            station=station,
            recorder=recorder,
            num_channels=_NUM_RECORDING_CHANNELS,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            creation_time=creation_time,
            creating_job=self._job)
        
        recording_channel = RecordingChannel.objects.create(
            recording=recording,
            channel_num=_RECORDING_CHANNEL_NUM,
            recorder_channel_num=_RECORDER_CHANNEL_NUM,
            mic_output=mic_output)
        
        return recording_channel


def _get_recording_channels_key(rc):
    recording = rc.recording
    station = recording.station
    return (station.name, station.get_night(recording.start_time))
    
    
def _get_audio_file_info(file_path):
    
    try:
        info = audio_file_utils.get_wave_file_info(file_path)
        
    except Exception:
        
        message = 'Could not get file length and sample rate.'
        
        try:
            size = os.path.getsize(file_path)
        except Exception:
            pass
        else:
            if size == 0:
                message = 'File is empty.'
            
        raise ValueError(message)
    
    else:
        return info.length, info.sample_rate
        

_FILE_NAME_REGEX = re.compile(
    r'^'
    r'(?P<detector_name>[^_]+)'
    r'_'
    r'(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)'
    r'_'
    r'(?P<hour>\d\d)\.(?P<minute>\d\d)\.(?P<second>\d\d)'
    r'_'
    r'(?P<num>\d\d)'
    r'\.wav'
    r'$')


def _parse_file_name(file_name):
    
    m = _FILE_NAME_REGEX.match(file_name)
    
    if m is not None:
        
        m = Bunch(**m.groupdict())
        
        try:
            start_time = time_utils.parse_date_time(
                m.year, m.month, m.day, m.hour, m.minute, m.second)
        except Exception as e:
            raise ValueError(
                'Could not get start time from file name: {}'.format(str(e)))
        
        tenths = datetime.timedelta(microseconds=100000 * int(m.num))
        start_time += tenths
        
        return m.detector_name, start_time
        
    else:
        raise ValueError('Could not parse file name.')


def _get_recording_start_and_end_times(station, date):
    
    try:
        infos = _RECORDING_DATA[station.name]
    except KeyError:
        raise ValueError(
            'No recording information available for station "{}".'.format(
                station.name))
    
    for info in infos:
        if info['start_date'] <= date and date <= info['end_date']:
            start_time = _get_recording_time(station, date, info['start_time'])
            end_time = _get_recording_time(station, date, info['end_time'])
            return start_time, end_time
        
    raise ValueError((
        'Could not find start and end times for recording from station "{}" '
        'on {}.').format(station.name, date))
            

def _get_recording_time(station, date, time):
    if time.hour < 12:
        date += _ONE_DAY
    return station.local_to_utc(datetime.datetime.combine(date, time))
    

def _assert_recording_contains_clip(recording, clip_start_time, clip_end_time):
    
    if clip_start_time < recording.start_time:
        raise ValueError(
            'Clip starts before recording that should contain it.')
    
    elif clip_end_time > recording.end_time:
        raise ValueError('Clip ends after recording that should contain it.')
    
    
def _copy_clip_audio_file(from_path, clip):
    to_path = clip_manager.get_audio_file_path(clip)
    os_utils.create_parent_directory(to_path)
    os_utils.copy_file(from_path, to_path)
