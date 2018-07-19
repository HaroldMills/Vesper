"""Module containing `ClipManager` class."""


from io import BytesIO

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.singletons import recording_manager
import vesper.util.audio_file_utils as audio_file_utils


class ClipManager:
    
    """Gets the audio data of the clips of a Vesper archive."""
    
    
    def __init__(self):
        self._rm = recording_manager.instance
        self._file_reader_cache = {}
        
        
    def get_wave_file_contents(self, clip):
        
        try:
            return clip.wav_file_contents
            
        except FileNotFoundError:
            
            contents = self._get_wave_file_contents_from_recording(clip)
            
            if contents is None:
                raise
            
            else:
                return contents
            
            
    def _get_wave_file_contents_from_recording(self, clip):
        
        samples = self.get_clip_samples_from_recording(clip)
        
        if samples is None:
            return None
        
        else:
            return _create_wave_file_contents(samples, clip.sample_rate)
            
            
    def get_clip_samples_from_recording(self, clip):
        
        if clip.start_index is None:
            # clip start index unknown
            
            return None
        
        for file_ in clip.recording.files.all():
            
            if clip.start_index >= file_.start_index and \
                    clip.start_index < file_.end_index:
                # Clip starts in this file.
                
                if clip.end_index < file_.end_index:
                    # Clip ends in this file.
                
                    return self._get_clip_samples_from_recording_file(
                        file_, clip)
                
                else:
                    
                    # TODO: Handle clips that cross file boundaries.
                    return None
                
        # If we get here, the clip was not found in a recording file.
        return None
    
    
    def _get_clip_samples_from_recording_file(self, file_, clip):
        
        try:
            path = self._rm.get_absolute_recording_file_path(file_.path)
        except ValueError as e:
            raise FileNotFoundError(str(e))
        
        reader = self._get_wave_file_reader(path)
        start_index = clip.start_index - file_.start_index
        samples = reader.read(start_index, clip.length)
        
        return samples[clip.channel_num]
    
    
    def _get_wave_file_reader(self, path):
        
        try:
            reader = self._file_reader_cache[path]
        
        except KeyError:
            # cache miss
            
            # Close cached reader. We cache just one reader at a time,
            # which goes a long way since in typical use our accesses
            # don't switch files very often.
            for reader in self._file_reader_cache.values():
                reader.close()
            
            # Create new reader.
            reader = WaveAudioFileReader(str(path))
            
            # Cache new reader.
            self._file_reader_cache[path] = reader
            
        return reader
    
    
def _create_wave_file_contents(samples, sample_rate):
    samples.shape = (1, len(samples))
    buffer = BytesIO()
    audio_file_utils.write_wave_file(buffer, samples, sample_rate)
    return buffer.getvalue()
