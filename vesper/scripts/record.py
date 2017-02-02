"""Records audio to .wav files according to a schedule."""


import argparse
import math
import wave

import pyaudio
import pytz
import yaml

from vesper.util.audio_recorder import AudioRecorder, AudioRecorderListener
from vesper.util.schedule import Schedule


_FILE_NAME_EXTENSION = '.wav'
_MAX_FILE_SIZE = 2**31          # two gigabytes (2**19 is good for testing)


def _main():
    
    config_file_path = _parse_args()
    
    (station_name, input_device_index, num_channels, sample_rate, buffer_size,
     schedule) = _parse_config_file(config_file_path)
    
    print('input device index', input_device_index)
    
    recorder = AudioRecorder(
        input_device_index, num_channels, sample_rate, buffer_size, schedule)
     
    # Add listeners.
    recorder.add_listener(_Logger())
    recorder.add_listener(_AudioFileWriter(station_name))
     
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
        
    input_device_index = _get_input_device_index(config.get('input_device'))
    num_channels = int(config['num_channels'])
    sample_rate = int(config['sample_rate'])
    buffer_size = int(config['buffer_size'])
    
    schedule = Schedule.compile_dict(
        config['schedule'], lat=lat, lon=lon, time_zone=time_zone)
    
    return (
        station_name, input_device_index, num_channels, sample_rate,
        buffer_size, schedule)
    
    
def _get_input_device_index(device):
    
    if device is None:
        return _get_default_input_device_index()

    else:
        
        try:
            return int(device)
        
        except ValueError:
            return _get_input_device_index_from_device_name(device)
    
    
def _get_default_input_device_index():
    
    pa = pyaudio.PyAudio()
    
    try:
        info = pa.get_default_input_device_info()
        
    except IOError:
        raise ValueError('No default input device available.')
    
    finally:
        pa.terminate()
        
    return info['index']
    

def _get_input_device_index_from_device_name(name):
    
    pa = pyaudio.PyAudio()
    
    # Get all device infos.
    num_devices = pa.get_device_count()
    infos = [pa.get_device_info_by_index(i) for i in range(num_devices)]
    
    pa.terminate()
    
    # Remove non-input device infos.
    infos = [i for i in infos if i['maxInputChannels'] != 0]
    
    if len(infos) == 0:
        raise ValueError('No input devices available.')
    
    # Find infos for devices whose names include `name`.
    infos = [i for i in infos if name in i['name']]
    
    if len(infos) == 0:
        raise ValueError(
            'No input device has a name that includes "{}".'.format(name))
        
    elif len(infos) > 1:
        raise ValueError(
            'More than one input device has a name that includes "{}".'.format(
                name))
        
    else:
        return infos[0]['index']
    
    
class _Logger(AudioRecorderListener):
    
    
    def recording_starting(self, recorder, time):
        print('recording_starting,{}'.format(time))
    
    
    def recording_started(self, recorder, time):
        print('recording_started,{}'.format(time))
        
        
    def samples_arrived(
            self, recorder, time, samples, num_frames, overflow, underflow):
        
        print(
            'samples_arrived,{},{},{},{}'.format(
                time, num_frames, overflow, underflow))
    
    
    def recording_stopped(self, recorder, time):
        print('recording_stopped,{}'.format(time))

    
class _AudioFileWriter(AudioRecorderListener):
    
    
    def __init__(self, station_name):
        self._station_name = station_name
        
        
    def recording_starting(self, recorder, time):
        
        self._num_channels = recorder.num_channels
        self._sample_rate = recorder.sample_rate
        self._sample_size = recorder.sample_size
        self._frame_size = self._num_channels * self._sample_size
        
        # We set the file size to one less than the largest integral number
        # of seconds of audio data that fit in the maximum file size. This
        # assumes that the non-audio data in the file (e.g. the header)
        # require no more space than than one second of audio data.
        bytes_per_second = self._sample_rate * self._frame_size
        max_seconds = int(math.floor(_MAX_FILE_SIZE / bytes_per_second)) - 1
        self._max_num_file_frames = max_seconds * self._sample_rate
        
        self._file_namer = _AudioFileNamer(
            self._station_name, _FILE_NAME_EXTENSION)
        
        self._file = None
        
    
    def samples_arrived(
            self, recorder, time, samples, num_frames, overflow, underflow):
        
        num_frames_remaining = num_frames
        buffer_index = 0
        
        while num_frames_remaining != 0:
            
            if self._file is None:
                self._file = self._open_audio_file(time)
                self._num_file_frames = 0
        
            num_frames = min(
                num_frames_remaining,
                self._max_num_file_frames - self._num_file_frames)
                
            num_bytes = num_frames * self._frame_size
            
            self._file.writeframes(
                samples[buffer_index:buffer_index + num_bytes])
            
            num_frames_remaining -= num_frames
            self._num_file_frames += num_frames
            buffer_index += num_bytes
            
            if self._num_file_frames == self._max_num_file_frames:
                self._file.close()
                self._file = None
    
    
    def _open_audio_file(self, time):
        
        file_name = self._file_namer.create_file_name(time)
        
        file_ = wave.open(file_name, 'wb')
        file_.setnchannels(self._num_channels)
        file_.setframerate(self._sample_rate)
        file_.setsampwidth(self._sample_size)
        
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
        return '{}_{}_Z{}'.format(
            self.station_name, time, self.file_name_extension)
        
        
def _show_event(name, time, state):
    print('{} at {} {}'.format(name, time, state))


if __name__ == '__main__':
    _main()
    