from datetime import timedelta as TimeDelta
from pathlib import Path
import wave

from vesper.recorder.processor import Processor
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


_DEFAULT_AUDIO_FILE_NAME_PREFIX = 'Vesper'
_DEFAULT_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_MAX_AUDIO_FILE_DURATION = 3600     # seconds

_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav'


class AudioFileWriter(Processor):
    
    
    name = 'Audio File Writer'


    @staticmethod
    def parse_settings(settings):

        audio_file_name_prefix = settings.get(
            'audio_file_name_prefix', _DEFAULT_AUDIO_FILE_NAME_PREFIX)

        recording_dir_path = Path(settings.get(
            'recording_dir_path', _DEFAULT_RECORDING_DIR_PATH))
        
        if not recording_dir_path.is_absolute():
            recording_dir_path = Path.cwd() / recording_dir_path
            
        max_audio_file_duration = settings.get(
            'max_audio_file_duration', _DEFAULT_MAX_AUDIO_FILE_DURATION)
        
        return Bunch(
            audio_file_name_prefix=audio_file_name_prefix,
            recording_dir_path=recording_dir_path,
            max_audio_file_duration=max_audio_file_duration)
    

    # TODO: Figure out how to get access to station name in initializer.
    # We don't want to have to specify the station name separately in
    # the settings for each audio file writer.
    def __init__(self, name, settings, input_info):
        
        super().__init__(name, settings, input_info)

        self._channel_count = input_info.channel_count
        self._sample_rate = input_info.sample_rate
        
        self._file_name_prefix = 'Vesper'
        self._recording_dir_path = settings.recording_dir_path
        self._max_audio_file_duration = settings.max_audio_file_duration
        
        # Create recording directory if needed.
        self._recording_dir_path.mkdir(parents=True, exist_ok=True)
        
        
    @property
    def file_name_prefix(self):
        return self._file_name_prefix
    

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
            self._file_name_prefix, _AUDIO_FILE_NAME_EXTENSION)
        
        self._file = None

        self._total_frame_count = 0
        
    
    def _process(self, input_item):
        
        samples = input_item.samples
        remaining_frame_count = input_item.frame_count
        buffer_index = 0
        
        while remaining_frame_count != 0:
            
            if self._file is None:
                self._file = self._open_audio_file()
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
                self._file = None
    
    
    def _open_audio_file(self):
        
        duration = self._total_frame_count / self._sample_rate
        time_delta = TimeDelta(seconds=duration)
        file_start_time = self._start_time + time_delta

        file_name = self._file_namer.create_file_name(file_start_time)
        file_path = self._recording_dir_path / file_name
        
        file_ = wave.open(str(file_path), 'wb')
        file_.setnchannels(self._channel_count)
        file_.setframerate(self._sample_rate)
        file_.setsampwidth(_SAMPLE_SIZE // 8)
        
        return file_
    

    def _stop(self):
        if self._file is not None:
            self._file.close()
        
    
class _AudioFileNamer:
    
    
    def __init__(self, file_name_prefix, file_name_extension):
        self.file_name_prefix = file_name_prefix
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.file_name_prefix}_{time}_Z{self.file_name_extension}'
