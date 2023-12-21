from datetime import timedelta as TimeDelta
from pathlib import Path
import logging
import wave

import vesper.recorder.async_task_thread as async_task_thread
from vesper.recorder.processor import Processor
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


_DEFAULT_AUDIO_FILE_NAME_PREFIX = 'Vesper'
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav'


_logger = logging.getLogger(__name__)


'''
Audio File Processors

When an audio file writer finishes writing a file, it will execute zero
or more *tasks* to process it. The tasks run on the recorder's
*async thread*. The async thread runs an asyncio event loop. The main
function of the event loop reads tasks from a `queue.Queue` and
runs them. Each task has an async `run` method that takes no arguments
and returns no value, and that's all that the async thread knows about
it. Tasks can log messages using Python's `logging` module.

The `AudioFileWriter` class will support postprocessing of audio files
that it writes via tasks called *audio file processors*. For example,
one type of audio file processor will upload an audio file to S3 and
then optionally delete it from the local file system.
'''


# RESUME:
#
# * Consider making async task thread a recorder property.
#
# * Consider giving `Processor` initializer a `context` argument
#   that for our purposes is a `VesperRecorder` object. This would
#   give processors access to the properties of a recorder, including
#   the async task thread, the station, etc.
#
# * Implement audio file writer `S3AudioFileUploader` async task and
#   test it. For now, hard code the task settings.
#
# * Implement `S3AudioFileUploader` task settings parsing.


class AudioFileWriter(Processor):
    
    
    name = 'Audio File Writer'


    @staticmethod
    def parse_settings(settings):

        recording_dir_path = Path(settings.get(
            'recording_dir_path', _DEFAULT_RECORDING_DIR_PATH))
        
        if not recording_dir_path.is_absolute():
            recording_dir_path = Path.cwd() / recording_dir_path
            
        audio_file_name_prefix = settings.get(
            'audio_file_name_prefix', _DEFAULT_AUDIO_FILE_NAME_PREFIX)

        max_audio_file_duration = settings.get(
            'max_audio_file_duration', _DEFAULT_MAX_AUDIO_FILE_DURATION)
        
        return Bunch(
            recording_dir_path=recording_dir_path,
            audio_file_name_prefix=audio_file_name_prefix,
            max_audio_file_duration=max_audio_file_duration)
    

    # TODO: Figure out how to get access to station name in initializer.
    # We don't want to have to specify the station name separately in
    # the settings for each audio file writer.
    def __init__(self, name, settings, input_info):
        
        super().__init__(name, settings, input_info)

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate
        
        self._recording_dir_path = settings.recording_dir_path
        self._audio_file_name_prefix = settings.audio_file_name_prefix
        self._max_audio_file_duration = settings.max_audio_file_duration
        
        # Create recording directory if needed.
        self._recording_dir_path.mkdir(parents=True, exist_ok=True)
        
        
    @property
    def audio_file_name_prefix(self):
        return self._audio_file_name_prefix
    

    @property
    def recording_dir_path(self):
        return self._recording_dir_path
    

    @property
    def max_audio_file_duration(self):
        return self._max_audio_file_duration
    

    def _start(self):
        
        self._start_time = time_utils.get_utc_now()

        self._frame_size = self._channel_count * _SAMPLE_SIZE // 8
        
        self._max_file_frame_count = \
            int(round(self._max_audio_file_duration * self._sample_rate))
                    
        self._file_namer = _AudioFileNamer(
            self._audio_file_name_prefix, _AUDIO_FILE_NAME_EXTENSION)
        
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
                self._process_audio_file()
                self._file = None
                self._file_path = None
    
    
    def _open_audio_file(self):
        
        duration = self._total_frame_count / self._sample_rate
        time_delta = TimeDelta(seconds=duration)
        file_start_time = self._start_time + time_delta

        file_name = self._file_namer.create_file_name(file_start_time)
        file_path = self._recording_dir_path / file_name
        
        file = wave.open(str(file_path), 'wb')
        file.setnchannels(self._channel_count)
        file.setframerate(self._sample_rate)
        file.setsampwidth(_SAMPLE_SIZE // 8)
        
        return file, file_path
    

    def _process_audio_file(self):
        _logger.info(
            f'AudioFileWriter: Submitting processing task for audio file '
            f'"{self._file_path}"...')
        task = _AudioFileProcessor(self._file_path)
        async_task_thread.instance.submit(task)
    

    def _stop(self):
        if self._file is not None:
            self._file.close()
            self._process_audio_file()
        
    
    def get_status_tables(self):

        recording_dir_path = self.recording_dir_path.absolute()

        rows = (
            ('Recording Directory', recording_dir_path),
            ('Audio File Name Prefix', self.audio_file_name_prefix),
            ('Max Audio File Duration (seconds)', self.max_audio_file_duration)
        )

        table = Bunch(title=self.name, rows=rows)

        return [table]


class _AudioFileNamer:
    
    
    def __init__(self, file_name_prefix, file_name_extension):
        self.file_name_prefix = file_name_prefix
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.file_name_prefix}_{time}_Z{self.file_name_extension}'
    

class _AudioFileProcessor:


    def __init__(self, file_path):
        self._file_path = file_path


    async def run(self):
        _logger.info(
            f'_AudioFileProcessor: processing audio file '
            f'"{self._file_path}"...')
