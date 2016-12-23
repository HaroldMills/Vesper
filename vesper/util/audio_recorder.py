"""Module containing the `AudioRecorder` class."""


from threading import Lock

import pyaudio

from vesper.util.notifier import Notifier


class AudioRecorder:
    
    """Records audio asynchronously."""
    
    
    # This class uses a lock to ensure that the `start`, `_callback`, and
    # `stop` methods execute atomically. These methods can run on various
    # threads, and making them atomic ensures that they have a coherent
    # view of the state of a recorder.
    

    def __init__(self, num_channels, sample_rate, buffer_size):
        self._num_channels = num_channels
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._recording = False
        self._notifier = Notifier()
        self._lock = Lock()
    
    
    @property
    def num_channels(self):
        return self._num_channels
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def buffer_size(self):
        return self._buffer_size
    
    
    @property
    def recording(self):
        return self._recording
    
    
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
    
    
    def remove_listener(self, listener):
        self._notiier.remove_listener(listener)
    
    
    def clear_listeners(self):
        self._notifier.clear_listeners()
    
    
    def _notify_listeners(self, method_name, *args, **kwargs):
        self._notifier.notify_listeners(method_name, self, *args, **kwargs)
            
            
    def start(self):
        
        with self._lock:
            
            if not self._recording:
                
                self._notify_listeners('recording_starting')
                    
                self._recording = True
                
                self._pyaudio = pyaudio.PyAudio()
                
                self._stream = self._pyaudio.open(
                    format=pyaudio.paInt16,
                    channels=self.num_channels,
                    rate=self.sample_rate,
                    frames_per_buffer=self.buffer_size,
                    input=True,
                    stream_callback=self._callback)
    
    
    def _callback(self, samples, buffer_size, time_info, status):
        
        with self._lock:
        
            if self._recording:
                self._notify_listeners('samples_arrived', samples, buffer_size)
                return (None, pyaudio.paContinue)
            
            else:
                return (None, pyaudio.paComplete)


    def stop(self):
        
        with self._lock:
            
            if self._recording:
                
                self._recording = False
                
                self._stream.stop_stream()
                self._stream.close()
                self._pyaudio.terminate()
                
                self._notify_listeners('recording_stopped')
