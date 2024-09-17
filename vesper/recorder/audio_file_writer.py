from datetime import timedelta as TimeDelta
from pathlib import Path
import wave

import numpy as np

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


_DEFAULT_AUDIO_FILE_NAME_PREFIX = 'Vesper'
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_CREATE_RECORDING_SUBDIRS = True
_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav.in_progress'


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
        
        return Bunch(
            recording_dir_path=recording_dir_path,
            create_recording_subdirs=create_recording_subdirs,
            audio_file_name_prefix=audio_file_name_prefix,
            max_audio_file_duration=max_audio_file_duration)
    

    def __init__(self, name, settings, context, input_info):
        
        super().__init__(name, settings, context, input_info)

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate
        
        self._recording_dir_path = settings.recording_dir_path
        self._create_recording_subdirs = settings.create_recording_subdirs
        self._audio_file_name_prefix = settings.audio_file_name_prefix
        self._max_audio_file_duration = settings.max_audio_file_duration

        # Create audio file processors, if specified.
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
        
    
    def _process(self, input_item, finished):
        
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
        output_items = []

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
                output_item = self._complete_audio_file()
                output_items.append(output_item)

        if finished and self._audio_file is not None:
            # all input has arrived and there's an open audio file
            # that is not yet full

            output_item = self._complete_audio_file()
            output_items.append(output_item)

        return output_items
    
    
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
    

    def _complete_audio_file(self):

        self._audio_file.close()

        # Get relative path of completed audio file, dropping
        # ".in_progress" extension from incomplete audio file path.
        completed_audio_file_path = self._audio_file_path.stem

        # Rename completed audio file.
        from_path = self._recording_dir_path / self._audio_file_path
        to_path = self._recording_dir_path / completed_audio_file_path
        from_path.rename(to_path)

        self._audio_file = None
        self._audio_file_path = None

        return (self._recording_dir_path, completed_audio_file_path)


    def get_status_tables(self):

        recording_dir_path = self.recording_dir_path.absolute()

        rows = (
            ('Recording Directory', recording_dir_path),
            ('Create Recording Subdirectories', self.create_recording_subdirs),
            ('Audio File Name Prefix', self.audio_file_name_prefix),
            ('Max Audio File Duration (seconds)', self.max_audio_file_duration)
        )

        table = StatusTable(self.name, rows)

        return [table]


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
