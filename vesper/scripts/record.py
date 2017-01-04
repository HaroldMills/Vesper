"""Records audio to .wav files according to a schedule."""


import argparse
import wave

import pytz
import yaml

from vesper.util.audio_recorder import AudioRecorder
from vesper.util.schedule import Schedule
import vesper.util.time_utils as time_utils


_FILE_NAME_EXTENSION = '.wav'


def _main():
    
    config_file_path = _parse_args()
    
    (station_name, num_channels, sample_rate, buffer_size, schedule) = \
        _parse_config_file(config_file_path)
    
    recorder = AudioRecorder(num_channels, sample_rate, buffer_size, schedule)
     
    # Add listener.
    recorder.add_listener(_Listener(station_name))
     
    # Start recording.
    print('starting recorder...')
    recorder.start()
     
    # Wait for recording schedule to complete.
    print('waiting for schedule to complete...')
    recorder.wait()
    print('schedule completed')
     
 
def _parse_args():
    parser = argparse.ArgumentParser(
        description='Records audio according to a schedule.')
    parser.add_argument('config_file_path', help='configuration file path')
    args = parser.parse_args()
    return args.config_file_path


def _parse_config_file(file_path):
    
    with open(file_path) as f:
        config = yaml.load(f)
        
    station_name = config['station']
    
    lat = config.get('latitude')
    if lat is not None:
        lat = float(lat)
        
    lon = config.get('longitude')
    if lon is not None:
        lon = float(lon)
        
    time_zone = config.get('time_zone')
    if time_zone is not None:
        time_zone = pytz.timezone(time_zone)
        
    num_channels = int(config['num_channels'])
    sample_rate = int(config['sample_rate'])
    buffer_size = int(config['buffer_size'])
    
    schedule = Schedule.compile_dict(
        config['schedule'], lat=lat, lon=lon, time_zone=time_zone)
    
    return (station_name, num_channels, sample_rate, buffer_size, schedule)
    
    
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
    