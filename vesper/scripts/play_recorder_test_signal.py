"""
Plays chirps repeatedly forever.

Different chirps can be configured for different channels.

I wrote this script to help test the Vesper recorder. Chirp test signals
should make it relatively easy to spot locations of dropped sample buffers
in test recording spectrograms.

The script allocates a fixed amount of sample memory before starting playback,
and does not allocate any sample memory during playback, including in the
PyAudio callback function.

In order to keep computation performed on the callback thread as simple as
possible, a separate thread called the *player thread* fills sample buffers
from precomputed chirps and feeds them to the callback thread via a queue
called the *filled buffer queue*. When it is done with a buffer, the callback
returns it to the player thread via a second queue called the
*free buffer queue*. The number of buffers is fixed, and the player thread
fills all of the buffers and writes them to the filled buffer queue before
starting the PyAudio output stream.
"""


from queue import Empty, Queue
from threading import Thread
import math
import time

import numpy as np
import pyaudio
import ruamel.yaml as yaml


_CONFIG = yaml.safe_load('''
    
    channel_signals:
    
        - signal_type: Chirp
          signal_config:
              amplitude: 10000
              start_freq: 0
              end_freq: 12000
              duration: 5.1
              
        - signal_type: Chirp
          signal_config:
              amplitude: 10000
              start_freq: 5000
              end_freq: 1000
              duration: 3.1
          
    sample_rate: 24000
    buffer_size: .1
    
''')

_SAMPLE_DTYPE = '<i2'
_SAMPLE_SIZE = 16          # bits
_BUFFER_SIZE = .2          # seconds
_TOTAL_BUFFER_SIZE = 10    # seconds
_TAPER_DURATION = .05      # seconds


def _main():
    
    audio_player = _create_audio_player()
    audio_player.start()
    
    print('Type Ctrl+C to stop playback and exit.')
    _wait_for_keyboard_interrupt()
    

def _create_audio_player():
    
    channel_configs = _CONFIG['channel_signals']
    sample_rate = _CONFIG['sample_rate']
    buffer_size = _CONFIG['buffer_size']
    
    signal_generator = \
        _create_signal_generator(channel_configs, sample_rate, _SAMPLE_DTYPE)
    
    return _AudioPlayer(
        signal_generator, sample_rate, _SAMPLE_SIZE, _SAMPLE_DTYPE,
        buffer_size, _TOTAL_BUFFER_SIZE)
    

def _create_signal_generator(channel_configs, sample_rate, sample_dtype):
    channel_generators = [
        _create_channel_generator(c, i, sample_rate, sample_dtype)
        for i, c in enumerate(channel_configs)]
    return _SignalGenerator(channel_generators)


def _create_channel_generator(config, channel_num, sample_rate, sample_dtype):
    creator = _SIGNAL_CREATORS[config['signal_type']]
    samples = creator(sample_rate, sample_dtype, **config['signal_config'])
    return _ChannelGenerator(channel_num, samples)
    
    
def _create_chirp(
        sample_rate, sample_dtype, amplitude, start_freq, end_freq, duration):
    
    # Compute chirp.
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    delta_freq = end_freq - start_freq
    freqs = start_freq + delta_freq * times / (2 * duration)
    phases = 2. * np.pi * freqs * times
    chirp = amplitude * np.sin(phases)
    
    # Taper ends.
    taper_length = int(round(_TAPER_DURATION * sample_rate))
    taper = np.arange(taper_length) / float(taper_length)
    chirp[:taper_length] *= taper
    chirp[-taper_length:] *= 1 - taper
    
    return chirp.astype(sample_dtype)

   
_SIGNAL_CREATORS = {
    'Chirp': _create_chirp
}


def _wait_for_keyboard_interrupt():
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass


class _SignalGenerator:
    
    
    def __init__(self, channel_generators):
        self._channel_generators = channel_generators
        
        
    @property
    def num_channels(self):
        return len(self._channel_generators)
    
    
    def generate_samples(self, buffer):
        for generator in self._channel_generators:
            generator.generate_samples(buffer)
    
    
class _ChannelGenerator:
    
    
    def __init__(self, channel_num, samples):
        self._channel_num = channel_num
        self._samples = samples
        self._index = 0
        self._length = len(samples)
        
        
    def generate_samples(self, buffer):
        
        """Generates the next buffer of samples of this channel's signal."""
        
        num_samples = buffer.num_frames
        
        remaining = num_samples
        
        while remaining != 0:
            
            n = min(remaining, self._length - self._index)
            
            i = num_samples - remaining
            buffer.channels[self._channel_num, i:i + n] = \
                self._samples[self._index:self._index + n]
            
            self._index = (self._index + n) % self._length
            remaining -= n

            
class _AudioPlayer:
    
    """Plays a generated audio signal asynchronously."""
    
    
    def __init__(
            self, signal_generator, sample_rate, sample_size, sample_dtype,
            buffer_size, total_buffer_size):
        
        self._signal_generator = signal_generator
        self._sample_rate = sample_rate
        self._sample_size = sample_size
        self._buffer_size = buffer_size
        
        # Create buffers to hold up to `total_buffer_size` seconds of
        # samples and put them onto free buffer queue.
        num_buffers = int(round(_TOTAL_BUFFER_SIZE / self.buffer_size))
        self._frames_per_buffer = \
            int(math.ceil(self.buffer_size * self.sample_rate))
        self._free_buffer_queue = Queue()
        for _ in range(num_buffers):
            buffer = _Buffer(
                self._frames_per_buffer, self.num_channels, sample_dtype)
            self._free_buffer_queue.put(buffer)
        
        # Create buffer filled with zeros to send on output underflow.
        bytes_per_frame = self.num_channels * self._sample_size
        bytes_per_buffer = self._frames_per_buffer * bytes_per_frame
        self._zeros_buffer = bytes(bytes_per_buffer)
        
        # Create queue for buffers that have been filled with samples
        # by the player thread.
        self._filled_buffer_queue = Queue()
        
        # Create player thread.
        self._thread = Thread(target=self._run, daemon=True)


    @property
    def num_channels(self):
        return self._signal_generator.num_channels
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def sample_size(self):
        return self._sample_size
    
    
    @property
    def buffer_size(self):
        return self._buffer_size
    
    
    def start(self):
        self._last_callback_buffer = None
        self._thread.start()


    def _run(self):
        
        # Pre-fill all audio buffers before starting playback.
        while not self._free_buffer_queue.empty():
            self._fill_next_free_buffer()
        
        pa = pyaudio.PyAudio()
        
        # Create PyAudio playback stream.
        stream = self._create_playback_stream(pa)
        
        # Start playback.
        stream.start_stream()
        
        # Refill audio buffers freed by the PyAudio callback.
        while True:
            self._fill_next_free_buffer()
            
        # We never get here, but if we did, this is what we'd do.
        stream.stop_stream()
        stream.close()
        pa.terminate()
        
            
    def _fill_next_free_buffer(self):
        buffer = self._free_buffer_queue.get()
        self._signal_generator.generate_samples(buffer)
        self._filled_buffer_queue.put(buffer)


    def _create_playback_stream(self, pa):
        
        audio_format = _get_audio_format(pa, self.sample_size)
        
        stream = pa.open(
            channels=self.num_channels,
            rate=self.sample_rate,
            format=audio_format,
            frames_per_buffer=self._frames_per_buffer,
            output=True,
            stream_callback=self._pyaudio_callback)
        
        return stream


    def _pyaudio_callback(self, _, num_frames, time_info, status):
        
        # Here we assume that whenever PyAudio calls this callback is is
        #  finished with the buffer that was last returned by the callback
        # (if there is one). I don't know that that is guaranteed, but it
        # seems reasonable, and it seems to work.
        if self._last_callback_buffer is not None:
            self._free_buffer_queue.put(self._last_callback_buffer)
            self._last_callback_buffer = None
            
        if num_frames != self._frames_per_buffer:
            print(
                ('PyAudio callback invoked for {} sample frames when '
                 'expecting {}.').format(num_frames, self._frames_per_buffer))
            
        try:
            buffer = self._filled_buffer_queue.get(block=False)
        except Empty:
            print('Output underflow in PyAudio callback.')
            return (self._zeros_buffer, pyaudio.paContinue)
        else:
            self._last_callback_buffer = buffer
            return (buffer.bytes, pyaudio.paContinue)


def _get_audio_format(pa, sample_size):
    bytes_per_sample = int(math.ceil(sample_size / 8))
    return pa.get_format_from_width(bytes_per_sample)
    
    
class _Buffer:
    
    def __init__(self, num_frames, num_channels, sample_dtype):
        self.num_frames = num_frames
        self.num_channels = num_channels
        self.frames = np.zeros((num_frames, num_channels), dtype=sample_dtype)
        self.channels = self.frames.T
        self.bytes = self.frames.view(dtype='i1')
        
        
if __name__ == '__main__':
    _main()
