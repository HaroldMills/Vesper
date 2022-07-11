from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis


class AudioFileSignal(Signal):
    
    
    def __init__(
            self, length, frame_rate, channel_count, dtype, name=None,
            file_path=None):
        
        time_axis = TimeAxis(length, frame_rate)
        item_shape = ()
        
        super().__init__(time_axis, channel_count, item_shape, dtype, name)
        
        self._file_path = file_path
        
        
    def __enter__(self):
        return self
    
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
        
        
    @property
    def file_path(self):
        return self._file_path
    
    
    @property
    def is_open(self):
        raise NotImplementedError()


    def close(self):
        raise NotImplementedError()
