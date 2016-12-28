"""Records audio asynchronously using the AudioRecorder class."""


import time
import wave

from vesper.util.audio_recorder import AudioRecorder


_NUM_CHANNELS = 1
_SAMPLE_RATE = 22050
_BUFFER_SIZE = 11025
_AUDIO_FILE_NAME = 'Vesper.wav'
_RECORDING_DURATION = 5


def _main():
    
    # Create recorder.
    recorder = AudioRecorder(_NUM_CHANNELS, _SAMPLE_RATE, _BUFFER_SIZE)
    
    # Add listener.
    listener = _Listener(_AUDIO_FILE_NAME)
    recorder.add_listener(listener)
    
    # Start recorder.
    recorder.start()
    
    # Pause for recording duration.
    time.sleep(_RECORDING_DURATION)
    
    # Tell recorder to stop.
    recorder.stop()
    
    # Wait for recorder to stop.
    recorder.wait()


class _Listener:
    
    
    def __init__(self, audio_file_path):
        self._audio_file_path = audio_file_path
        
        
    def recording_starting(self, recorder):
        print('recording_starting')
        f = wave.open(self._audio_file_path, 'wb')
        f.setnchannels(recorder.num_channels)
        f.setframerate(recorder.sample_rate)
        f.setsampwidth(2)
        self._file = f
    
    
    def samples_arrived(self, recorder, samples, buffer_size):
        # print('samples_arrived', buffer_size)
        self._file.writeframes(samples)
    
    
    def recording_stopped(self, recorder):
        print('recording_stopped')
        self._file.close()
    
    
if __name__ == '__main__':
    _main()
    