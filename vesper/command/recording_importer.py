"""Module containing class `RecordingImporter`."""


import itertools
import logging
import os

from django.db import transaction

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import (
    DeviceConnection, Job, Recording, RecordingChannel, RecordingFile, Station)
from vesper.singletons import extension_manager, preset_manager
import vesper.command.command_utils as command_utils
import vesper.command.recording_utils as recording_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


class RecordingImporter:
    
    """
    Importer for recordings already stored in files on the Vesper server.
    
    The recordings to be imported are specified in the `paths` argument
    as server-side directory and file paths. Files from directories can
    be imported either recursively or non-recursively according to the
    `recursive` argument. The import does not copy or move recordings:
    it stores the existing paths of their files for future reference.
    
    The importer obtains recording metadata for imported files with the
    aid of a recording file parser extension, specified by the
    `recording_file_parser` argument.
    """
    
    
    extension_name = 'Recording Importer'
    
    
    def __init__(self, args):
        self.paths = command_utils.get_required_arg('paths', args)
        self.recursive = command_utils.get_optional_arg('recursive', args, True)
        spec = command_utils.get_optional_arg('recording_file_parser', args)
        self.file_parser = _create_file_parser(spec)
    
    
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)
        self._logger = logging.getLogger()
        
        try:
            
            recordings = self._get_recordings()
            
            new_recordings, old_recordings = \
                self._partition_recordings(recordings)
                
            self._log_header(new_recordings, old_recordings)
            
            with transaction.atomic():
                self._import_recordings(new_recordings)
            
        except Exception as e:
            self._logger.error((
                'Recording import failed with an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise
        
        else:
            self._log_imports(new_recordings)

        return True
            
            
    def _get_recordings(self):
        files = list(itertools.chain.from_iterable(
            self._get_path_recording_files(path) for path in self.paths))
        return recording_utils.group_recording_files(files)

                
    def _get_path_recording_files(self, path):
        
        if os.path.isdir(path):
            return self._get_dir_recording_files(path)
        
        else:
            file = self._get_recording_file(path)
            return [] if file is None else [file]


    def _get_dir_recording_files(self, path):
        
        files = []
            
        for (dir_path, dir_names, file_names) in os.walk(path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                file = self._get_recording_file(file_path)
                if file is not None:
                    files.append(file)
                
            if not self.recursive:
                
                # Stop `os.walk` from descending into subdirectories.
                del dir_names[:]
                
        return files
                
                
    def _get_recording_file(self, file_path):
        
        if not audio_file_utils.is_wave_file_path(file_path):
            return None
        
        else:
            
            try:
                f = self.file_parser.parse_file(file_path)
            
            except ValueError as e:
                raise CommandExecutionError(
                    'Error parsing recording file "{}": {}'.format(
                        file_path, str(e)))
                
            if f.recorder is None:
                f.recorder = _get_recorder(f)
                
            _set_recording_file_channel_info(f)
                
            return f
            
    
    def _partition_recordings(self, recordings):
        
        new_recordings = []
        old_recordings = []
        
        for r in recordings:
            
            if self._recording_exists(r):
                old_recordings.append(r)
                
            else:
                new_recordings.append(r)
                
        return (new_recordings, old_recordings)
    
                
    def _recording_exists(self, recording):
        
        try:
            Recording.objects.get(
                station=recording.station,
                recorder=recording.recorder,
                start_time=recording.start_time)
            
        except Recording.DoesNotExist:
            return False
        
        else:
            return True
            

    def _log_header(self, new_recordings, old_recordings):
        
        log = self._logger.info
        
        new_count = len(new_recordings)
        old_count = len(old_recordings)
        
        if new_count == 0 and old_count == 0:
            log('Found no recordings at the specified paths.')
            
        else:
            new_text = self._get_num_recordings_text(new_count, 'new')
            old_text = self._get_num_recordings_text(old_count, 'old')
            log('Found {} and {} at the specified paths.'.format(
                new_text, old_text))

        if len(new_recordings) == 0:
            self._logger.info('No recordings will be imported.')
            
        else:
            self._logger.info('The new recordings will be imported.')
            

    def _get_num_recordings_text(self, count, description):
        suffix = '' if count == 1 else 's'
        return '{} {} recording{}'.format(count, description, suffix)
        
        
    def _import_recordings(self, recordings):
    
        for r in recordings:
            
            end_time = signal_utils.get_end_time(
                r.start_time, r.length, r.sample_rate)
            
            creation_time = time_utils.get_utc_now()
            
            recording = Recording(
                station=r.station,
                recorder=r.recorder,
                num_channels=r.num_channels,
                length=r.length,
                sample_rate=r.sample_rate,
                start_time=r.start_time,
                end_time=end_time,
                creation_time=creation_time,
                creating_job=self._job)
            
            recording.save()
            
            r.model = recording
            
            for channel_num in range(r.num_channels):
                
                recorder_channel_num = r.recorder_channel_nums[channel_num]
                mic_output = r.mic_outputs[channel_num]
            
                channel = RecordingChannel(
                    recording=recording,
                    channel_num=channel_num,
                    recorder_channel_num=recorder_channel_num,
                    mic_output=mic_output)
                
                channel.save()
                
            start_index = 0         
            
            for file_num, f in enumerate(r.files):
                
                file = RecordingFile(
                    recording=recording,
                    file_num=file_num,
                    start_index=start_index,
                    length=f.length,
                    path=f.path)
                
                file.save()
                
                start_index += f.length
                

    def _log_imports(self, recordings):
        for r in recordings:
            log = self._logger.info
            log('Imported recording {} with files:'.format(str(r.model)))
            for f in r.files:
                log('    {}'.format(f.path))
            

def _create_file_parser(spec):
    
    # Get stations.
    stations = [s for s in Station.objects.all()]
    
    # Get station name aliases.
    parser_classes = \
        extension_manager.instance.get_extensions('Recording File Parser')
    parser_class = parser_classes[spec['name']]
    args = spec.get('arguments', {})
    preset_name = args['station_name_aliases_preset']
    preset = \
        preset_manager.instance.get_preset('Station Name Aliases', preset_name)
    station_name_aliases = preset.data
    
    return parser_class(stations, station_name_aliases)


def _get_recorder(file):
    
    end_time = signal_utils.get_end_time(
        file.start_time, file.length, file.sample_rate)

    station_recorders = file.station.get_station_devices(
        'Audio Recorder', file.start_time, end_time)
    
    if len(station_recorders) == 0:
        raise CommandExecutionError('Could not find recorder for file.')
    
    elif len(station_recorders) > 1:
        raise CommandExecutionError(
            'Found more than one possible recorder for file.')
    
    else:
        return station_recorders[0].device
        
        
def _set_recording_file_channel_info(f):
    
    mic_outputs = _get_recorder_mic_outputs(f.recorder, f.start_time)
    
    if f.recorder_channel_nums is None:
        # file name did not indicate recorder channel numbers
        
        if len(mic_outputs) != f.num_channels:
            # number of connected mic outputs does not match number
            # of file channels
            
            raise CommandExecutionError((
                'Could not infer recorder channel numbers for '
                'recording file "{}".').format(f.path))
            
        else:
            # number of connected mic outputs matches number of file
            # channels
            
            # We assume that recorder inputs map to file channel numbers
            # in increasing order.
            f.recorder_channel_nums = tuple(sorted(mic_outputs.keys()))
            
    
    f.mic_outputs = tuple(
        _get_mic_output(mic_outputs, i, f.path)
        for i in f.recorder_channel_nums)
        
        
def _get_recorder_mic_outputs(recorder, time):
     
    """
    Gets a mapping from recorder input channel numbers to connected
    microphone outputs for the specified recorder and time.
    """
     
    connections = DeviceConnection.objects.filter(
        input__device=recorder,
        output__device__model__type='Microphone',
        start_time__lte=time,
        end_time__gt=time)
     
    # print('recording_importer.get_recorder_mic_outputs', connections.query)
     
    return dict((c.input.channel_num, c.output) for c in connections)


def _get_mic_output(mic_outputs, channel_num, file_path):
    
    try:
        return mic_outputs[channel_num]
    
    except KeyError:
        raise CommandExecutionError((
            'Could not find microphone output connected to recorder input '
            '{} for recording file "{}".').format(channel_num, file_path))
        