from datetime import timedelta as TimeDelta
from pathlib import Path
import asyncio
import itertools
import logging
import wave

import numpy as np

from vesper.recorder.processor import Processor
from vesper.recorder.s3_audio_file_uploader import S3AudioFileUploader
from vesper.recorder.settings import Settings
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.recorder.async_task_thread as async_task_thread
import vesper.util.time_utils as time_utils


_chain = itertools.chain.from_iterable


_DEFAULT_AUDIO_FILE_NAME_PREFIX = 'Vesper'
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_CREATE_RECORDING_SUBDIRS = True
_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds
_DEFAULT_DELETE_SUCCESSFULLY_PROCESSED_AUDIO_FILES = False

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav'

_AUDIO_FILE_PROCESSOR_CLASSES = (S3AudioFileUploader,)


_logger = logging.getLogger(__name__)


'''
Audio File Processors

When an audio file writer finishes writing a file, it runs zero or
more *audio file processors* to process it. The processors run
concurrently with each other on the recorder's *async task thread*.

The async task thread of a recorder runs an asyncio event loop.
The main function of the event loop reads tasks from a `queue.Queue`
and runs them. Each task has an async `run` method that takes no
arguments and returns no value, and that's all that the async thread
knows about it. Tasks can log messages using Python's `logging` module.
They should log messages for any errors that occur during their
execution.

An audio file processor is an object with a `run` method that takes
the recording directory path and the path relative to that of an
audio file, processes the file in some way, and returns no value.
If an error occurs in the `run` method, the method should log an
error message and raise an exception.

To process an audio file that it has written, the audio file writer
creates a task for the async task thread that invokes the `run`
methods of its audio file processors concurrently on the file.
If all of the `run` methods complete normally, it optionally deletes
the processed file, according to the audio file writer's
`delete_successfully_processed_audio_files` setting. If any of the
`run` methods raises an exception, it does not delete the processed
file.

At this time the only implemented audio file processor is one that
uploads an audio file to AWS S3. In the future, additional processors
might upload an audio file to other cloud storage services or trigger
some sort of file processing external to the Vesper Recorder.
'''


# RESUME:
#
# * Consider making async task thread a recorder property.
#
# * Consider giving `Processor` initializer a `context` argument
#   that for our purposes is a `VesperRecorder` object. This would
#   give processors access to the properties of a recorder, including
#   the async task thread, the station, etc.


class AudioFileWriter(Processor):
    
    
    type_name = 'Audio File Writer'


    @staticmethod
    def parse_settings(settings):

        recording_dir_path = Path(settings.get(
            'recording_dir_path', _DEFAULT_RECORDING_DIR_PATH)).expanduser()
        
        if not recording_dir_path.is_absolute():
            recording_dir_path = Path.cwd() / recording_dir_path

        create_recording_subdirs = settings.get(
            'create_recording_subdirs', _DEFAULT_CREATE_RECORDING_SUBDIRS)
            
        audio_file_name_prefix = settings.get(
            'audio_file_name_prefix', _DEFAULT_AUDIO_FILE_NAME_PREFIX)

        max_audio_file_duration = settings.get(
            'max_audio_file_duration', _DEFAULT_MAX_AUDIO_FILE_DURATION)
        
        audio_file_processors = _parse_audio_file_processor_settings(settings)

        delete_successfully_processed_audio_files = settings.get(
            'delete_successfully_processed_audio_files',
            _DEFAULT_DELETE_SUCCESSFULLY_PROCESSED_AUDIO_FILES)

        return Bunch(
            recording_dir_path=recording_dir_path,
            create_recording_subdirs=create_recording_subdirs,
            audio_file_name_prefix=audio_file_name_prefix,
            max_audio_file_duration=max_audio_file_duration,
            audio_file_processors=audio_file_processors,
            delete_successfully_processed_audio_files=
                delete_successfully_processed_audio_files)
    

    # TODO: Figure out how to get access to station name in initializer.
    # We don't want to have to specify the station name separately in
    # the settings for each audio file writer.
    def __init__(self, name, settings, input_info):
        
        super().__init__(name, settings, input_info)

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate
        
        self._recording_dir_path = settings.recording_dir_path
        self._create_recording_subdirs = settings.create_recording_subdirs
        self._audio_file_name_prefix = settings.audio_file_name_prefix
        self._max_audio_file_duration = settings.max_audio_file_duration

        # Create audio file processors, if specified.
        self._audio_file_processors = \
            _create_audio_file_processors(settings.audio_file_processors)
        
        self._delete_successfully_processed_audio_files = \
            settings.delete_successfully_processed_audio_files

        # Create recording subdir namer.
        if self._create_recording_subdirs:
            self._recording_subdir_namer = _RecordingSubdirNamer(
                self._audio_file_name_prefix)
            
        # Create audio file namer.
        self._audio_file_namer = _AudioFileNamer(
            self._audio_file_name_prefix, _AUDIO_FILE_NAME_EXTENSION)
        
        # Get audio file sample frame size in bytes.
        self._frame_size = self._channel_count * _SAMPLE_SIZE // 8
        
        # Get max audio file size in sample frames.
        self._max_file_frame_count = \
            int(round(self._max_audio_file_duration * self._sample_rate))
                    
        
    @property
    def recording_dir_path(self):
        return self._recording_dir_path
    

    @property
    def create_recording_subdirs(self):
        return self._create_recording_subdirs
    

    @property
    def audio_file_name_prefix(self):
        return self._audio_file_name_prefix
    

    @property
    def max_audio_file_duration(self):
        return self._max_audio_file_duration
    

    @property
    def delete_successfully_processed_audio_files(self):
        return self._delete_successfully_processed_audio_files
    

    def _start(self):
        
        self._start_time = time_utils.get_utc_now()

        if self._create_recording_subdirs:
            subdir_name = self._recording_subdir_namer.create_subdir_name(
                self._start_time)
            self._recording_subdir_path = Path(subdir_name)
        else:
            self._recording_subdir_path = None

        self._audio_file = None
        self._audio_file_path = None

        self._total_frame_count = 0
        
    
    def _process(self, input_item):
        
        # TODO: Consider using (and reusing) more pre-allocated buffers
        # in the following, to reduce memory churn.
        # Transpose, scale, round, and clip samples, convert to int16,
        # and get resulting bytes.
        samples = input_item.samples[:, :input_item.frame_count].transpose()
        samples = 32768 * samples
        np.rint(samples, out=samples)
        np.clip(samples, -32768, 32767, out=samples)
        samples = np.array(samples, dtype='int16').tobytes()
            
        remaining_frame_count = input_item.frame_count
        buffer_index = 0
        
        while remaining_frame_count != 0:
            
            if self._audio_file is None:
                self._audio_file, self._audio_file_path = \
                    self._open_audio_file()
                self._file_frame_count = 0
        
            frame_count = min(
                remaining_frame_count,
                self._max_file_frame_count - self._file_frame_count)
                
            byte_count = frame_count * self._frame_size
            
            self._audio_file.writeframes(
                samples[buffer_index:buffer_index + byte_count])
            
            remaining_frame_count -= frame_count
            self._file_frame_count += frame_count
            self._total_frame_count += frame_count
            buffer_index += byte_count
            
            if self._file_frame_count == self._max_file_frame_count:
                self._audio_file.close()
                self._process_audio_file()
                self._audio_file = None
                self._audio_file_path = None
    
    
    def _open_audio_file(self):
        
        # Get audio file name.
        duration = self._total_frame_count / self._sample_rate
        time_delta = TimeDelta(seconds=duration)
        file_start_time = self._start_time + time_delta
        file_name = self._audio_file_namer.create_file_name(file_start_time)

        # Get audio file path relative to recording directory.
        if self._create_recording_subdirs:
            rel_file_path = self._recording_subdir_path / file_name
        else:
            rel_file_path = Path(file_name)
        
        # Get absolute audio file path.
        abs_file_path = self._recording_dir_path / rel_file_path

        # Create ancestor directories for audio file as needed.
        dir_path = abs_file_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        # Create audio file.
        file = wave.open(str(abs_file_path), 'wb')
        file.setnchannels(self._channel_count)
        file.setframerate(self._sample_rate)
        file.setsampwidth(_SAMPLE_SIZE // 8)
        
        return file, rel_file_path
    

    def _process_audio_file(self):

        processors = self._audio_file_processors

        if len(processors) != 0:

            task = _AudioFileProcessorTask(
                processors, self._recording_dir_path, self._audio_file_path,
                self._delete_successfully_processed_audio_files)
           
            _logger.info(
                f'Submitting task to process completed audio file '
                f'"{self._audio_file_path}"...')
            
            async_task_thread.instance.submit(task)
    

    def _stop(self):
        if self._audio_file is not None:
            self._audio_file.close()
            self._process_audio_file()
        
    
    def get_status_tables(self):

        recording_dir_path = self.recording_dir_path.absolute()

        rows = (
            ('Recording Directory', recording_dir_path),
            ('Create Recording Subdirectories', self.create_recording_subdirs),
            ('Audio File Name Prefix', self.audio_file_name_prefix),
            ('Max Audio File Duration (seconds)', self.max_audio_file_duration)
        )

        table = StatusTable(self.name, rows)

        processor_tables = list(_chain(
            p.get_status_tables() for p in self._audio_file_processors))

        return [table] + processor_tables


def _parse_audio_file_processor_settings(settings):

    settings = settings.get('audio_file_processors')

    if settings is None:
        return []
    
    elif not isinstance(settings, list):
        raise ValueError(
            f'Bad type "{settings.__class__.__name__}" for audio file '
            f'writer "audio_file_processors" setting: type must be "list".')

    else:
        # setting is present and is a `list``

        processor_classes = \
            {cls.type_name: cls for cls in _AUDIO_FILE_PROCESSOR_CLASSES}

        return [
            _parse_audio_file_processor_settings_aux(s, processor_classes)
            for s in settings]
    

def _parse_audio_file_processor_settings_aux(settings, processor_classes):
        
        settings = Settings(settings)

        name = settings.get_required('name')
        type = settings.get_required('type')
        mapping = settings.get('settings', {})                                                                        

        try:
            cls = processor_classes[type]
        except KeyError:
            raise ValueError(
                f'Unrecognized audio file processor type "{type}".')
        
        settings = cls.parse_settings(Settings(mapping))

        return Bunch(
            name=name,
            type=type,
            settings=settings)
    

def _create_audio_file_processors(settings):

    processor_classes = \
        {cls.type_name: cls for cls in _AUDIO_FILE_PROCESSOR_CLASSES}

    return \
        [_create_audio_file_processor(s, processor_classes) for s in settings]


def _create_audio_file_processor(settings, processor_classes):
    cls = processor_classes[settings.type]
    return cls(settings.name, settings.settings)


class _RecordingSubdirNamer:


    def __init__(self, subdir_name_prefix):
        self.subdir_name_prefix = subdir_name_prefix


    def create_subdir_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.subdir_name_prefix}_{time}_Z'


class _AudioFileNamer:
    
    
    def __init__(self, file_name_prefix, file_name_extension):
        self.file_name_prefix = file_name_prefix
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.file_name_prefix}_{time}_Z{self.file_name_extension}'


class _AudioFileProcessorTask:


    def __init__(
            self, processors, recording_dir_path, audio_file_path,
            delete_successfully_processed_audio_file):
        
        self._processors = processors
        self._recording_dir_path = recording_dir_path
        self._audio_file_path = audio_file_path
        self._delete_successfully_processed_audio_file = \
            delete_successfully_processed_audio_file


    async def run(self):

        # TODO: Consider using an `asyncio.TaskGroup` in this method
        # instead of `asyncio.gather`. I think that would require that
        # all of the coroutines handle their own exceptions. To be sure,
        # perhaps we could call each processor's `run` method from a
        # coroutine that catches any exception that it raises.

        try:

            coroutines =  [
                p.process_file(self._recording_dir_path, self._audio_file_path)
                for p in self._processors]
        
            # Run coroutines concurrently.
            await asyncio.gather(*coroutines)

        except:
            # something went wrong in one of the coroutines

            # The coroutines other than the one that raised the exception
            # will keep running, and if any of them raise exceptions we
            # won't hear about it. However, each coroutine is responsible
            # for logging error messages concerning its operation.

            fileProcessingFailed = True

        else:
            # no coroutine raised an exception

            fileProcessingFailed = False

        if self._delete_successfully_processed_audio_file:

            audio_file_path = self._recording_dir_path / self._audio_file_path

            if fileProcessingFailed:
                _logger.warning(
                    f'Processing failed for completed audio file '
                    f'"{audio_file_path}". File will not be deleted.')
                
            else:
                # file processing succeeded

                self._delete_audio_file(audio_file_path)
                self._delete_empty_audio_file_ancestor_dirs()
                    

    def _delete_audio_file(self, audio_file_path):

        _logger.info(
            f'Deleting successfully processed audio file '
            f'"{audio_file_path}"...')
        
        try:
            audio_file_path.unlink()

        except Exception as e:
            _logger.warning(
                f'Could not delete audio file "{audio_file_path}". '
                f'Exception message was: {e}')
            

    def _delete_empty_audio_file_ancestor_dirs(self):

        """
        Deletes the directories of `self._audio_file_path.parents[:-1]`
        up until the first non-empty directory. Does not consider
        `self._audio_file_path.parents[-1]` since it is always '.'.
        """


        if self._audio_file_path.is_absolute():

            _logger.error(
                'Internal Vesper Recorder error: encountered absolute '
                'audio file path in `_AudioFileProcessorTask.'
                '_delete_empty_audio_file_ancestor_dirs`. Expected '
                'a relative path. No directories will be deleted.')
            
            return
            
        for rel_dir_path in self._audio_file_path.parents[:-1]:

            # We could just invoke `dir_path.rmdir` instead of checking
            # if the directory is empty first, and ignore any exception
            # that it raises. That should work, deleting an empty
            # directory and doing nothing for a non-empty one. Even so,
            # I would feel uncomfortable invoking `dir_path.rmdir` on
            # directories that I know I don't want to delete, counting
            # on that method to protect me from disaster! It also
            # wouldn't allow us to detect failed attempts to delete
            # empty directories.

            abs_dir_path = self._recording_dir_path / rel_dir_path

            child_paths = tuple(abs_dir_path.iterdir())

            if len(child_paths) == 0:
                # directory empty

                _logger.warning(
                    f'Deleting empty recording subdirectory '
                    f'"{abs_dir_path}"...')
                    
                try:
                    abs_dir_path.rmdir()

                except Exception as e:
                    _logger.warning(
                        f'Could not delete empty recording subdirectory '
                        f'"{abs_dir_path}". Error message was: {e}')
                    
            else:
                # directory not empty

                # We can stop here, since any further directories will
                # be ancestors of this one, and hence not empty, either.
                break
