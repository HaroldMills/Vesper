from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis


'''
Design of Vesper audio file signals:

* Support various audio file formats through plugins.

* WaveFileSignal plugin supports WAVE files via the Python `wave` module.

* AiffFileSignal plugin supports AIFF files via the Python `aifc` module.

* Optional SoundFileSignal plugin supports various kinds of audio files
  via the SoundFile package. I would like for this plugin to be optional
  in the sense that if you won't use it you don't have to install the
  SoundFile package and its dependencies.

* Audio file signal class initializer accepts a file path or a file-like
  object. Raises an `UnsupportedAudioFileError` if the file is not supported.
'''


class AudioFileSignal(Signal):
    
    
    def __init__(
            self, length, frame_rate, channel_count, dtype, sample_provider,
            name=None, file_path=None, file_format=None):
        
        time_axis = TimeAxis(length, frame_rate)
        array_shape = ()
        
        super().__init__(
            time_axis, channel_count, array_shape, dtype, sample_provider,
            name)
        
        self._file_path = file_path
        self._file_format = file_format
        
        
    @property
    def file_path(self):
        return self._file_path
    
    
    @property
    def file_format(self):
        return self._file_format
