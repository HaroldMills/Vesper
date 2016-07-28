"""Module containing class `AudioFileReader`."""


class AudioFileReader:
    
    """Abstract base class for audio file readers."""
    

    def __init__(
            self, file_path, file_type, num_channels, length, sample_rate,
            dtype, mono_1d=False):
        
        self._file_path = file_path
        self._file_type = file_type
        self._num_channels = num_channels
        self._length = length
        self._sample_rate = sample_rate
        self._dtype = dtype
        self._mono_1d = mono_1d
        
        
    def __enter__(self):
        return self
    
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
        
        
    @property
    def file_path(self):
        return self._file_path
    
    
    @property
    def file_type(self):
        return self._file_type
    
    
    @property
    def num_channels(self):
        return self._num_channels
    
    
    @property
    def length(self):
        return self._length
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def dtype(self):
        return self._dtype
    
    
    @property
    def mono_1d(self):
        return self._mono_1d
    
    
    def read(self, start_index=0, length=None):
        raise NotImplementedError()
    
    
    def close(self):
        raise NotImplementedError()
