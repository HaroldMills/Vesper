"""Records audio to .wav files according to a schedule."""


import wave

from vesper.util.audio_recorder import AudioRecorder
from vesper.util.schedule import Schedule
import vesper.util.time_utils as time_utils


_STATION_NAME = 'Vesper'
_TIME_ZONE = 'US/Eastern'
_NUM_CHANNELS = 1
_SAMPLE_RATE = 22050
_BUFFER_SIZE = 22050
_FILE_NAME_EXTENSION = '.wav'

_SCHEDULE = '''
    intervals:
        - start: 2016-12-28 11:04 am
          duration: 5 seconds
'''


def _main():
    
    # Create schedule.
    schedule = Schedule.compile_yaml(_SCHEDULE, time_zone=_TIME_ZONE)
    
    # Create recorder.
    recorder = AudioRecorder(
        _NUM_CHANNELS, _SAMPLE_RATE, _BUFFER_SIZE, schedule)
     
    # Add listener.
    listener = _Listener(_STATION_NAME)
    recorder.add_listener(listener)
     
    # Start recording.
    print('starting recorder...')
    recorder.start()
     
    # Wait for recording schedule to complete.
    print('waiting for schedule to complete...')
    recorder.wait()
    print('schedule completed')
     
 
class _Listener:
    
    
    def __init__(self, station_name):
        self._file_namer = _FileNamer(station_name, _FILE_NAME_EXTENSION)
        self._file_name = None
        self._file = None
        
        
    def recording_starting(self, recorder):
        
        time = time_utils.get_utc_now()
        self._file_name = self._file_namer.create_file_name(time)
        
        print('recording_starting file "{}"...'.format(self._file_name))
        
        f = wave.open(self._file_name, 'wb')
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
        
    
class _FileNamer:
    
    
    def __init__(self, station_name, file_name_extension):
        self.station_name = station_name
        self.file_name_extension = file_name_extension
        
        
    def create_file_name(self, start_time):
        time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
        return '{}_{}_Z{}'.format(
            self.station_name, time, self.file_name_extension)
        
        
def _show_event(name, time, state):
    print('{} at {} {}'.format(name, time, state))


if __name__ == '__main__':
    _main()
    