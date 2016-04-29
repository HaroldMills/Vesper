"""Utility functions pertaining to audio files."""


from vesper.signal.wave_audio_file_type import WaveAudioFileType


_AUDIO_FILE_TYPES = (
    WaveAudioFileType(),
)


class UnrecognizedAudioFileType(Exception):
    pass


def get_file_type(file_):
    
    for file_type in _AUDIO_FILE_TYPES:
        if file_type.is_recognized_file(file_):
            return file_type
        
    # If we get here, the file was not recognized by any audio file type.
    return None
    
    
def _get_file_type(file_):
    
    file_type = get_file_type(file_)
    
    if file_type is None:
        raise UnrecognizedAudioFileType(
            'File is not of any recognized audio file type.')
        
    else:
        return file_type
        
        
def get_file_info(file_):
    file_type = _get_file_type(file_)
    return file_type.get_file_info(file_)
    
    
def read_file(file_):
    file_type = _get_file_type(file_)
    return file_type.read_file(file_)


def open_file(file_):
    file_type = _get_file_type(file_)
    return file_type.open_file(file_)


'''
Audio file I/O issues:

* Reading an entire audio file into memory to create a signal or
  multichannel signal is a very common use case. The code for this
  should be very straightforward, e.g.:
  
      sound = audio_file_utils.read_file(file_path)
      sound = audio_file_utils.read_file(file_path)[0]
      
* Want to allow construction of both signals and multichannel signals.

* Want to allow construction of both eager and lazy waveforms.

  For an eager waveform, the entire audio file is read in one go. The
  file is opened and closed within the function that constructs the
  waveform.
  
  For a lazy waveform, samples are read from the audio file only on demand.
  The file may remain open across multiple reads.
  
* An `AudioFileType` can recognize audio files of one or more types,
  read metadata from a recognized file, and open a file for reading
  and/or writing via a `Signal`.

In the following, if `file_` is a string it must be a file path,
otherwise it must be a file-like object.

class AudioFileType(object):
    
    @property
    def read_only(self):
        pass
    
    def is_recognized_file(self, file_):
        pass
    
    def get_file_info(self, file_):
        pass
    
    def read_file(self, file_):
        pass
    
    def write_file(self, file_, sound, info):
        pass
    
    def open_file(self, file_, mode, info):
        pass
        
Examples:

    info = audio_file_utils.get_file_info(file_path)
    
    with audio_file_utils.open_file(file_path, 'r') as sound:
        samples = sound[...]
        
    with audio_file_utils.open_file(file_path, 'w', info) as sound:
        sound.append(samples)
'''