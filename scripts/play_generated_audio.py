"""
Plays chirps repeatedly forever.

Different chirps can be configured for different channels.

I wrote this script to help test the Vesper recorder. Chirp test signals
should make it relatively easy to spot locations of dropped sample buffers
in test recording spectrograms.
"""


import math
import time

import numpy as np
import pyaudio
import yaml


_CONFIG = yaml.load('''
    
    channel_signals:
    
        - signal_type: Chirp
          signal_config:
              amplitude: 10000
              start_freq: 0
              end_freq: 10000
              duration: 5.1
              
        - signal_type: Chirp
          signal_config:
              amplitude: 10000
              start_freq: 5000
              end_freq: 1000
              duration: 3.1
          
    sample_rate: 22050
    sample_size: 16
    
''')

_SAMPLE_DTYPE = '<i2'


def _main():
    
    channel_configs = _CONFIG['channel_signals']
    num_channels = len(channel_configs)
    sample_rate = _CONFIG['sample_rate']
    sample_size = _CONFIG['sample_size']
    
    generator = _create_signal_generator(sample_rate, channel_configs)
    
    pa = pyaudio.PyAudio()
     
    audio_format = _get_audio_format(pa, sample_size)
     
    stream = pa.open(
        format=audio_format,
        channels=num_channels,
        rate=sample_rate,
        output=True,
        stream_callback=generator.callback)
     
    stream.start_stream()
     
    while stream.is_active():
        time.sleep(.1)
     
    stream.stop_stream()
    stream.close()
     
    pa.terminate()


def _get_audio_format(pa, sample_size):
    bytes_per_sample = int(math.ceil(sample_size / 8))
    return pa.get_format_from_width(bytes_per_sample)
    
    
def _create_signal_generator(sample_rate, channel_configs):
    channel_generators = [
        _create_channel_generator(sample_rate, c) for c in channel_configs]
    return _PeriodicSignalGenerator(channel_generators)


def _create_channel_generator(sample_rate, config):
    creator = _SIGNAL_CREATORS[config['signal_type']]
    samples = creator(sample_rate, **config['signal_config'])
    return _BufferRepeater(samples)
    
    
def _create_chirp(sample_rate, amplitude, start_freq, end_freq, duration):
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    delta_freq = end_freq - start_freq
    freqs = start_freq + delta_freq * times / (2 * duration)
    phases = 2. * np.pi * freqs * times
    samples = (amplitude * np.sin(phases)).astype(_SAMPLE_DTYPE)
    return samples

   
_SIGNAL_CREATORS = {
    'Chirp': _create_chirp
}


class _PeriodicSignalGenerator:
    
    
    def __init__(self, channel_generators):
        self._channel_generators = channel_generators
        
        
    def callback(self, _, num_frames, time_info, status):
        channels = [g.get_samples(num_frames) for g in self._channel_generators]
        samples = np.vstack(channels).T.ravel()
        bytes = samples.tobytes()
        return (bytes, pyaudio.paContinue)
    
    
class _BufferRepeater:
    
    
    def __init__(self, samples):
        self._samples = samples
        self._index = 0
        self._length = len(samples)
        
        
    def get_samples(self, num_samples):
        
        """
        Generates the next `num_samples` samples of this generator's signal.
        The samples are returned in a NumPy array of 16-bit integers.
        """
        
        
        samples = np.zeros(num_samples, dtype=_SAMPLE_DTYPE)
        
        remaining = num_samples
        
        while remaining != 0:
            
            n = min(remaining, self._length - self._index)
            
            i = num_samples - remaining
            samples[i:i + n] = self._samples[self._index:self._index + n]
            
            self._index = (self._index + n) % self._length
            remaining -= n
            
        return samples

            
if __name__ == '__main__':
    _main()
    