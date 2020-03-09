"""Module containing class `ExecuteDeferredActionsCommand`."""


import datetime
import logging
import pickle
import time

from django.db import transaction
import pytz

from vesper.archive_paths import archive_paths
from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import (
    AnnotationInfo, Clip, Job, Processor, RecordingChannel)
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.signal_utils as signal_utils


_LOGGING_PERIOD = 10000


class ExecuteDeferredActionsCommand(Command):
    
    
    extension_name = 'execute_deferred_actions'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        self._recording_channel_cache = {}
        self._job_cache = {}
        self._processor_cache = {}
        self._annotation_info_cache = {}
    
    
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)
        self._logger = logging.getLogger()
        
        dir_path = archive_paths.deferred_action_dir_path
        
        if not dir_path.exists():
            self._logger.info((
                'There are no deferred actions to execute, since '
                'the directory "{}" does not exist.').format(dir_path))
            
        elif not dir_path.is_dir():
            raise CommandExecutionError(
                'The path "{}" exists but is not a directory.'.format(
                    dir_path))
            
        else:

            file_paths = sorted(dir_path.glob('*.pkl'))
            num_files = len(file_paths)
            
            self._logger.info((
                'Executing deferred actions from {} files of directory '
                '"{}"...').format(num_files, dir_path))
                
            try:
                with transaction.atomic():
                    for i, file_path in enumerate(file_paths):
                        self._logger.info((
                            'Executing actions from file {} of {} - '
                            '"{}"...').format(
                                i + 1, num_files, file_path.name))
                        self._execute_deferred_actions(file_path)
              
            except Exception:
                self._logger.error(
                    'Execution of deferred actions failed with an '
                    'exception. Archive database has been restored '
                    'to its state before the job began. See below '
                    'for exception traceback.')
                raise
            
            # If we get here, the execution of all of the deferred
            # actions succeeded and we can move the action files
            # to the `Executed` directory.
            self._move_deferred_action_files(file_paths)
              
        return True
    
    
    def _execute_deferred_actions(self, file_path):
        
        with open(file_path, 'rb') as file_:
            data = pickle.load(file_)
            
        actions = data.get('actions', [])
        
        for action in actions:
            self._execute_deferred_action(action)
            
            
    def _execute_deferred_action(self, action):
        
        name = action['name']
        args = action['arguments']
        
        if name == 'create_clips':
            self._execute_create_clips_action(args)
            
        
    def _execute_create_clips_action(self, args):
        
        clips = args['clips']
        num_clips = len(clips)
        
        self._logger.info('Creating {} clips...'.format(num_clips))
        
        start_time = time.time()
        
        clip_num = 0
        
        for clip in clips:
            
            self._create_clip(clip)
            
            clip_num += 1
            
            if clip_num % _LOGGING_PERIOD == 0:
                self._logger.info('Created {} clips...'.format(clip_num))
                    
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, num_clips, 'clips')
        self._logger.info(
            'Created {} clips{}.'.format(num_clips, timing_text))


    def _create_clip(self, clip_info):
        
        (recording_channel_id, start_index, length, creation_time,
         creating_job_id, creating_processor_id, annotations) = clip_info
         
        channel, station, mic_output, sample_rate, start_time = \
            self._get_recording_channel_info(recording_channel_id)
            
        start_offset = signal_utils.get_duration(start_index, sample_rate)
        start_time += datetime.timedelta(seconds=start_offset)
        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
            
        job = self._get_job(creating_job_id)
        processor = self._get_processor(creating_processor_id)
         
        clip = Clip.objects.create(
            station=station,
            mic_output=mic_output,
            recording_channel=channel,
            start_index=start_index,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            date=station.get_night(start_time),
            creation_time=creation_time,
            creating_user=None,
            creating_job=job,
            creating_processor=processor
        )
        
        if annotations is not None:
            
            for name, value in annotations.items():
                
                annotation_info = self._get_annotation_info(name)
                
                model_utils.annotate_clip(
                    clip, annotation_info, str(value),
                    creation_time=creation_time, creating_user=None,
                    creating_job=self._job, creating_processor=processor)


    # TODO: The `_get_annotation_info` method and the code above that
    # calls it were copied from the `detect_command` module. Consider
    # refactoring so there is just one public copy of the code that is
    # invoked from both places.
    def _get_annotation_info(self, name):
        
        try:
            return self._annotation_info_cache[name]
        
        except KeyError:
            # cache miss
            
            try:
                info = AnnotationInfo.objects.get(name=name)
            
            except AnnotationInfo.DoesNotExist:
                
                # For now, at least, we require that there already be an
                # `AnnotationInfo` in the archive database for any
                # annotation that a detector wants to create.
                raise ValueError((
                    'Annotation "{}" not found in archive database: '
                    'please add it and try again.').format(name))
                
            else:
                self._annotation_info_cache[name] = info
                return info

        
    def _get_recording_channel_info(self, recording_channel_id):

        try:
            return self._recording_channel_cache[recording_channel_id]
        
        except KeyError:
            
            channel = RecordingChannel.objects.get(id=recording_channel_id)
            recording = channel.recording
            station = recording.station
            mic_output = channel.mic_output
             
            sample_rate = recording.sample_rate
            start_time = recording.start_time
            
            info = (channel, station, mic_output, sample_rate, start_time)
            
            self._recording_channel_cache[recording_channel_id] = info
            
            return info
        
        
    def _get_job(self, job_id):
        
        try:
            return self._job_cache[job_id]
        
        except KeyError:
            job = Job.objects.get(id=job_id)
            self._job_cache[job_id] = job
            return job

         
    def _get_processor(self, processor_id):
        
        try:
            return self._processor_cache[processor_id]
        
        except KeyError:
            processor = Processor.objects.get(id=processor_id)
            self._processor_cache[processor_id] = processor
            return processor
        
        
    def _move_deferred_action_files(self, file_paths):
        
        if len(file_paths) > 0:
            
            self._logger.info(
                'Moving deferred action files to "Executed" directory...')
            
            executed_dir_path = file_paths[0].parent / 'Executed'
            executed_dir_path.mkdir(parents=True, exist_ok=True)
            
            for old_path in file_paths:
                new_path = executed_dir_path / old_path.name
                old_path.rename(new_path)
        
         
def _parse_datetime(dt):
    dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    return pytz.utc.localize(dt)
