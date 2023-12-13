import wave

from vesper.recorder.audio_recorder import AudioRecorderListener


_AUDIO_FILE_NAME_EXTENSION = '.wav'


class AudioFileWriter(AudioRecorderListener):
    
    
    def __init__(self, station_name, recording_dir_path, max_file_duration):
        
        super().__init__()
        
        self._station_name = station_name
        self._recording_dir_path = recording_dir_path
        self._max_file_duration = max_file_duration
        
        # Create recording directory if needed.
        self._recording_dir_path.mkdir(parents=True, exist_ok=True)
        
        
    @property
    def station_name(self):
        return self._station_name
    

    @property
    def recording_dir_path(self):
        return self._recording_dir_path
    

    @property
    def max_file_duration(self):
        return self._max_file_duration
    

    def recording_starting(self, recorder, time):
        
        self._channel_count = recorder.channel_count
        self._sample_rate = recorder.sample_rate
        self._sample_size = recorder.sample_size
        self._frame_size = self._channel_count * self._sample_size // 8
        self._zeros = bytearray(recorder.frames_per_buffer * self._frame_size)
        
        self._max_file_frame_count = \
            int(round(self._max_file_duration * self._sample_rate))
                    
        self._file_namer = _AudioFileNamer(
            self._station_name, _AUDIO_FILE_NAME_EXTENSION)
        
        self._file = None
        
    
    def input_arrived(
            self, recorder, time, samples, frame_count, portaudio_overflow):
        self._write_samples(time, samples, frame_count)
        
        
    def _write_samples(self, time, samples, frame_count):
        
        remaining_frame_count = frame_count
        buffer_index = 0
        
        while remaining_frame_count != 0:
            
            if self._file is None:
                self._file = self._open_audio_file(time)
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
            buffer_index += byte_count
            
            if self._file_frame_count == self._max_file_frame_count:
                self._file.close()
                self._file = None
    
    
    def input_overflowed(
            self, recorder, time, frame_count, portaudio_overflow):
        self._write_samples(time, self._zeros, frame_count)
    
        
    def _open_audio_file(self, time):
        
        file_name = self._file_namer.create_file_name(time)
        file_path = self._recording_dir_path / file_name
        
        file_ = wave.open(str(file_path), 'wb')
        file_.setnchannels(self._channel_count)
        file_.setframerate(self._sample_rate)
        file_.setsampwidth(self._sample_size // 8)
        
        return file_
    

    def recording_stopped(self, recorder, time):
        if self._file is not None:
            self._file.close()
        
    
class _AudioFileNamer:
    
    
    def __init__(self, station_name, file_name_extension):
        self.station_name = station_name
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return f'{self.station_name}_{time}_Z{self.file_name_extension}'
