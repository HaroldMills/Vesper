"""Module containing class `RecordingImporter`."""


from pathlib import Path
import itertools
import logging
import os

from django.db import transaction

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import (
    DeviceConnection, Job, Recording, RecordingChannel, RecordingFile)
from vesper.singleton.recording_manager import recording_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.command.recording_utils as recording_utils
import vesper.util.file_type_utils as file_type_utils
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
        self.recursive = command_utils.get_optional_arg(
            'recursive', args, True)
        spec = command_utils.get_optional_arg('recording_file_parser', args)
        self.file_parser = recording_utils.create_recording_file_parser(spec)
    
    
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)
        self._logger = logging.getLogger()
        
        try:
            
            recordings = self._get_new_recordings()
            
            self._log_header(recordings)
            
            with transaction.atomic():
                self._import_recordings(recordings)
            
        except Exception as e:
            self._logger.error(
                f'Recording import failed with an exception.\n'
                f'The exception message was:\n'
                f'    {str(e)}\n'
                f'The archive was not modified.\n'
                f'See below for exception traceback.')
            raise
        
        else:
            self._log_imports(recordings)
        
        return True
    
    
    def _get_new_recordings(self):
        files = self._get_unimported_disk_files()
        return recording_utils.group_recording_files(files)
    
    
    def _get_unimported_disk_files(self):
        
        db_files = RecordingFile.objects.all()
        db_file_paths = frozenset(r.path for r in db_files)
        
        disk_file_infos = list(itertools.chain.from_iterable(
            self._get_path_recording_file_infos(path) for path in self.paths))
        
        unimported_disk_files = []
        
        for info in disk_file_infos:
            path = str(info.relative_path)
            if path not in db_file_paths:
                file = self._parse_recording_file(info.absolute_path)
                file.path = info.relative_path
                _set_recording_file_channel_info(file)
                unimported_disk_files.append(file)
        
        return unimported_disk_files
    
    
    def _get_path_recording_file_infos(self, path):
        
        if os.path.isdir(path):
            return self._get_dir_recording_file_infos(path)
        
        else:
            file = self._get_recording_file_info(path)
            return [] if file is None else [file]
    
    
    def _get_dir_recording_file_infos(self, path):
        
        files = []
        
        for (dir_path, dir_names, file_names) in os.walk(path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                file = self._get_recording_file_info(Path(file_path))
                if file is not None:
                    files.append(file)
                
            if not self.recursive:
                
                # Stop `os.walk` from descending into subdirectories.
                del dir_names[:]
                
        return files
    
    
    def _get_recording_file_info(self, file_path):
        
        if not file_type_utils.is_wave_file(file_path):
            return None
        
        else:
            return self._get_recording_file_path_info(file_path)
    
    
    def _get_recording_file_path_info(self, file_path):
        
        if file_path.is_absolute():
            
            if not file_path.exists():
                raise CommandExecutionError(
                    f'Purported recording file "{file_path}" does not exist.')
                
            return self._get_absolute_path_info(file_path)
        
        else:
            # path is relative
            
            return self._get_relative_path_info(file_path)
    
    
    def _get_relative_path_info(self, file_path):
        
        rm = recording_manager
        
        try:
            abs_path = rm.get_absolute_recording_file_path(file_path)
            
        except ValueError:
            self._handle_bad_recording_file_path(
                file_path, 'could not be found in', rm)
            
        return Bunch(absolute_path=abs_path, relative_path=file_path)
    
    
    def _handle_bad_recording_file_path(self, file_path, condition, manager):
        
        dir_paths = manager.recording_dir_paths
        
        if len(dir_paths) == 1:
            s = f'the recording directory "{dir_paths[0]}"'
        else:
            path_list = str(list(dir_paths))
            s = f'any of the recording directories {path_list}'
            
        raise CommandExecutionError(
            f'Recording file "{file_path}" {condition} {s}.')
    
    
    def _get_absolute_path_info(self, file_path):
        
        rm = recording_manager
        
        try:
            _, rel_path = rm.get_relative_recording_file_path(file_path)
            
        except ValueError:
            self._handle_bad_recording_file_path(file_path, 'is not in', rm)
            
        return Bunch(absolute_path=file_path, relative_path=rel_path)
    
    
    def _parse_recording_file(self, file_path):
        
        try:
            file = self.file_parser.parse_file(str(file_path))
        
        except ValueError as e:
            raise CommandExecutionError(
                f'Error parsing recording file "{file_path}": {str(e)}')
            
        if file.recorder is None:
            file.recorder = _get_recorder(file)
            
        return file
    
    
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
            db_recording = Recording.objects.get(
                station=recording.station,
                recorder=recording.recorder,
                start_time=recording.start_time)
            
        except Recording.DoesNotExist:
            return False
        
        else:
            # found recording in database with same station, recorder,
            # and start time as files on disk
            
            if db_recording.length != recording.length:
                # length of recording in database differs from length
                # of files
                
                # In this case we warn about the problem but do not
                self._logger.warning(
                    f'For recording "{str(db_recording)}", length '
                    f'{db_recording.length} of recording indicated in '
                    f'archive database differs from length '
                    f'{recording.length} of files found on disk. No '
                    f'action will be taken regarding this recording.')
                
            return True
    
    
    def _log_header(self, recordings):
        
        log = self._logger.info
        
        recording_count = len(recordings)
        
        if recording_count == 0:
            log('Found no new recordings at the specified paths.')
            log('No recordings will be imported.')

        else:
            log(f'Found {recording_count} new recordings at the '
                f'specified paths.')
            log('The new recordings will be imported.')
    
    
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
                
                # We store all paths in the archive database as POSIX
                # paths, even on Windows, for portability, since Python's
                # `pathlib` module recognizes the slash as a path separator
                # on all platforms, but not the backslash.
                path = f.path.as_posix()
                
                file = RecordingFile(
                    recording=recording,
                    file_num=file_num,
                    start_index=start_index,
                    length=f.length,
                    path=path)
                
                file.save()
                
                start_index += f.length
    
    
    def _log_imports(self, recordings):
        for r in recordings:
            log = self._logger.info
            log(f'Imported recording {str(r.model)} with files:')
            for f in r.files:
                log(f'    {f.path.as_posix()}')
    
    
def _get_recorder(file):
    
    end_time = signal_utils.get_end_time(
        file.start_time, file.length, file.sample_rate)

    station_recorders = file.station.get_station_devices(
        'Audio Recorder', file.start_time, end_time)
    
    if len(station_recorders) == 0:
        raise CommandExecutionError(
            f'Could not find recorder for recording file "{file.path}".')
    
    elif len(station_recorders) > 1:
        raise CommandExecutionError(
            f'Found more than one possible recorder for file "{file.path}".')
    
    else:
        return station_recorders[0].device
    
    
def _set_recording_file_channel_info(file):
    
    mic_outputs = _get_recorder_mic_outputs(file.recorder, file.start_time)
    
    if file.recorder_channel_nums is None:
        # file name did not indicate recorder channel numbers
        
        if len(mic_outputs) != file.num_channels:
            # number of connected mic outputs does not match number
            # of file channels
            
            raise CommandExecutionError(
                f'Could not infer recorder channel numbers for '
                f'recording file "{file.path}".')
            
        else:
            # number of connected mic outputs matches number of file
            # channels
            
            # We assume that recorder inputs map to file channel numbers
            # in increasing order.
            file.recorder_channel_nums = tuple(sorted(mic_outputs.keys()))
            
            
    file.mic_outputs = tuple(
        _get_mic_output(mic_outputs, i, file.path)
        for i in file.recorder_channel_nums)
    
    
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
        raise CommandExecutionError(
            f'Could not find microphone output connected to recorder input '
            f'{channel_num} for recording file "{file_path}".')
