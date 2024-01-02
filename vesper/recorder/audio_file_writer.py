from datetime import timedelta as TimeDelta
from pathlib import Path
import logging
import wave

from vesper.recorder.processor import Processor
from vesper.recorder.s3_audio_file_uploader import S3AudioFileUploader
from vesper.recorder.settings import Settings
from vesper.util.bunch import Bunch
import vesper.recorder.async_task_thread as async_task_thread
import vesper.util.time_utils as time_utils


_DEFAULT_AUDIO_FILE_NAME_PREFIX = 'Vesper'
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_CREATE_RECORDING_SUBDIRS = True
_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav'

_AUDIO_FILE_PROCESSOR_CLASSES = (S3AudioFileUploader,)


_logger = logging.getLogger(__name__)


'''
Audio File Processors

When an audio file writer finishes writing a file, it optionally
executes an *audio file processor* to process it. The processor runs
as a task on the recorder's *async task thread*. The async task thread
runs an asyncio event loop. The main function of the event loop reads
tasks from a `queue.Queue` and runs them. Each task has an async `run`
method that takes no arguments and returns no value, and that's all
that the async thread knows about it. Tasks can log messages using
Python's `logging` module.

At this time the only implemented audio file processor is one that
uploads an audio file to AWS S3, optionally deleting the file if the
upload is successful.
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
    
    
    name = 'Audio File Writer'


    @staticmethod
    def parse_settings(settings):

        recording_dir_path = Path(settings.get(
            'recording_dir_path', _DEFAULT_RECORDING_DIR_PATH))
        
        if not recording_dir_path.is_absolute():
            recording_dir_path = Path.cwd() / recording_dir_path

        create_recording_subdirs = settings.get(
            'create_recording_subdirs', _DEFAULT_CREATE_RECORDING_SUBDIRS)
            
        audio_file_name_prefix = settings.get(
            'audio_file_name_prefix', _DEFAULT_AUDIO_FILE_NAME_PREFIX)

        max_audio_file_duration = settings.get(
            'max_audio_file_duration', _DEFAULT_MAX_AUDIO_FILE_DURATION)
        
        audio_file_processor = _parse_audio_file_processor_settings(settings)

        return Bunch(
            recording_dir_path=recording_dir_path,
            create_recording_subdirs=create_recording_subdirs,
            audio_file_name_prefix=audio_file_name_prefix,
            max_audio_file_duration=max_audio_file_duration,
            audio_file_processor=audio_file_processor)
    

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

        # Get audio file processor class, if specified.
        self._audio_file_processor_class = \
            _get_audio_file_processor_class(settings.audio_file_processor)

        # Create recording subdir namer.
        if self._create_recording_subdirs:
            self._recording_subdir_namer = _RecordingSubdirNamer(
                self._audio_file_name_prefix)
            
        # Create audio file namer.
        self._file_namer = _AudioFileNamer(
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
    

    def _start(self):
        
        self._start_time = time_utils.get_utc_now()

        if self._create_recording_subdirs:

            dir_name = self._recording_subdir_namer.create_subdir_name(
                self._start_time)
            
            self._recording_subdir_path = self._recording_dir_path / dir_name

        self._file = None
        self._file_path = None

        self._total_frame_count = 0
        
    
    def _process(self, input_item):
        
        samples = input_item.samples
        remaining_frame_count = input_item.frame_count
        buffer_index = 0
        
        while remaining_frame_count != 0:
            
            if self._file is None:
                self._file, self._file_path = self._open_audio_file()
                self._file_frame_count = 0
        
            frame_count = min(
                remaining_frame_count,
                self._max_file_frame_count - self._file_frame_count)
                
            byte_count = frame_count * self._frame_size
            
            # TODO: We assume here that the sample bytes are in
            # little-endian order, but perhaps we shouldn't.
            self._file.writeframes(
                samples[buffer_index:buffer_index + byte_count])
            
            remaining_frame_count -= frame_count
            self._file_frame_count += frame_count
            self._total_frame_count += frame_count
            buffer_index += byte_count
            
            if self._file_frame_count == self._max_file_frame_count:
                self._file.close()
                self._process_audio_file_if_needed()
                self._file = None
                self._file_path = None
    
    
    def _open_audio_file(self):
        
        # Get audio file parent directory path.
        if self._create_recording_subdirs:
            dir_path = self._recording_subdir_path
        else:
            dir_path = self._recording_dir_path

        # Get audio file name.
        duration = self._total_frame_count / self._sample_rate
        time_delta = TimeDelta(seconds=duration)
        file_start_time = self._start_time + time_delta
        file_name = self._file_namer.create_file_name(file_start_time)

        # Get audio file path.
        file_path = dir_path / file_name
        
        # Create parent directory if needed.
        dir_path.mkdir(parents=True, exist_ok=True)

        # Create audio file.
        file = wave.open(str(file_path), 'wb')
        file.setnchannels(self._channel_count)
        file.setframerate(self._sample_rate)
        file.setsampwidth(_SAMPLE_SIZE // 8)
        
        return file, file_path
    

    def _process_audio_file_if_needed(self):

        settings = self._settings.audio_file_processor

        if settings is not None:
             
            _logger.info(
                f'Submitting task to process audio file '
                f'"{self._file_path}"...')
            
            settings = settings.settings
            task = self._audio_file_processor_class(
                settings, self._file_path, self._create_recording_subdirs)
            async_task_thread.instance.submit(task)
    

    def _stop(self):
        if self._file is not None:
            self._file.close()
            self._process_audio_file_if_needed()
        
    
    def get_status_tables(self):

        recording_dir_path = self.recording_dir_path.absolute()

        rows = (
            ('Recording Directory', recording_dir_path),
            ('Create Recording Subdirectories', self.create_recording_subdirs),
            ('Audio File Name Prefix', self.audio_file_name_prefix),
            ('Max Audio File Duration (seconds)', self.max_audio_file_duration)
        )

        table = Bunch(title=self.name, rows=rows)

        return [table]


def _parse_audio_file_processor_settings(settings):

    mapping = settings.get('audio_file_processor')

    if mapping is None:
        return None
    
    else:

        processor_classes = \
            {cls.name: cls for cls in _AUDIO_FILE_PROCESSOR_CLASSES}

        settings = Settings(mapping)

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
    

def _get_audio_file_processor_class(settings):

    if settings is None:
        return None
    
    else:
        # have audio file processor settings

        processor_classes = \
            {cls.name: cls for cls in _AUDIO_FILE_PROCESSOR_CLASSES}
        
        return processor_classes[settings.type]


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
