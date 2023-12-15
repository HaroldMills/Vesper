from datetime import timedelta as TimeDelta
import wave

from vesper.recorder.processor import Processor


_SAMPLE_SIZE = 16
_AUDIO_FILE_NAME_EXTENSION = '.wav'


class AudioFileWriter(Processor):
    
    
    def __init__(self, name, settings, input, station_name):
        
        super().__init__(name, settings, input)

        self._channel_count = input.channel_count
        self._sample_rate = input.sample_rate
        
        self._station_name = station_name
        self._recording_dir_path = settings.recording_dir_path
        self._max_audio_file_duration = settings.max_audio_file_duration
        
        # Create recording directory if needed.
        self._recording_dir_path.mkdir(parents=True, exist_ok=True)
        
        
    @property
    def station_name(self):
        return self._station_name
    

    @property
    def recording_dir_path(self):
        return self._recording_dir_path
    

    @property
    def max_audio_file_duration(self):
        return self._max_audio_file_duration
    

    def _start(self):
        
        self._frame_size = self._channel_count * _SAMPLE_SIZE // 8
        
        self._max_file_frame_count = \
            int(round(self._max_audio_file_duration * self._sample_rate))
                    
        self._file_namer = _AudioFileNamer(
            self._station_name, _AUDIO_FILE_NAME_EXTENSION)
        
        self._file = None

        self._total_frame_count = 0
        
    
    def _process(self, item):
        
        samples = item.samples
        remaining_frame_count = item.frame_count
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
    
    
    def __init__(self, station_name, file_name_extension):
        self.station_name = station_name
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.station_name}_{time}_Z{self.file_name_extension}'
