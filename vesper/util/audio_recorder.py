"""Module containing the `AudioRecorder` class."""


import pyaudio


class AudioRecorder:
    
    """Uses PyAudio to record audio asynchronously."""
    
    
    def __init__(self, num_channels, sample_rate, buffer_size):
        self._num_channels = num_channels
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._recording = False
        self._listeners = set()
    
    
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
        self._listeners.add(listener)
        
        
    def start(self):
        
        if not self._recording:
            
            for listener in self._listeners:
                listener.recording_starting(
                    self.num_channels, self.sample_rate);
                
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
        
        if self._recording:
            
            for listener in self._listeners:
                listener.samples_arrived(samples, buffer_size)
            
            return (None, pyaudio.paContinue)
        
        else:
            return (None, pyaudio.paComplete)


    def stop(self):
        
        if self._recording:
            
            self._recording = False
            
            self._stream.stop_stream()
            self._stream.close()
            self._pyaudio.terminate()
            
            for listener in self._listeners:
                listener.recording_stopped()
