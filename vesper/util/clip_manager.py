"""Module containing `ClipManager` class."""


from io import BytesIO
from threading import Lock

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.singletons import recording_manager
import vesper.util.audio_file_utils as audio_file_utils


class ClipManager:
    
    """Gets the audio data of the clips of a Vesper archive."""
    
    
    def __init__(self):
        self._rm = recording_manager.instance
        self._file_reader_cache = {}
        self._read_lock = Lock()
        
        
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
        
        # TODO: Make search for a file's clip more efficient.
        # The following code is O(n), where n is the number of
        # recording files, but we could make it O(log(n)) by
        # using a more efficient search algorithm. This will
        # require cacheing lists of recording files for recordings,
        # which is fine.
        
        for file_ in clip.recording.files.all():
            
            if clip.start_index >= file_.start_index and \
                    clip.start_index < file_.end_index:
                # Clip starts in this file.
                
                if clip.end_index < file_.end_index:
                    # Clip ends in this file.
                
                    return self._read_clip_samples_from_recording_file(
                        file_, clip)
                
                else:
                    
                    # TODO: Handle clips that cross file boundaries.
                    return None
                
        # If we get here, the clip was not found in a recording file.
        return None
    
    
    def _read_clip_samples_from_recording_file(self, file_, clip):
        
        try:
            path = self._rm.get_absolute_recording_file_path(file_.path)
        except ValueError as e:
            raise FileNotFoundError(str(e))
        
        # Since the file reader cache may be shared among threads, we
        # use a lock to make getting a file reader for a clip and reading
        # samples from it atomic.
        #
        # Without the lock, we have observed that reads can return the
        # wrong samples. For example, suppose that this method is called
        # on separate threads for two different clips, clips 1 and 2,
        # that are in the same file and hence will use the same file
        # reader. We want the seek and read operations for the two clips
        # to be ordered like this:
        #
        #     1. Seek clip 1.
        #     2. Read clip 1.
        #     3. Seek clip 2.
        #     4. Read clip 2.
        #
        # (or perhaps with operations 3 and 4 preceding 1 and 2). If we
        # don't make the seek/read combinations atomic, however, we can
        # get this instead:
        #
        #     1. Seek clip 1.
        #     2. Seek clip 2.
        #     3. Read clip 1.
        #     4. Read clip 2.
        #
        # which reads the wrong samples for both clips.
        #
        # If we don't make the combination of getting the file reader
        # for a clip and reading from the reader atomic, the following
        # can happen when we try to read two clips whose samples are in
        # different files:
        #
        #     1. Get reader for clip 1.
        #     2. Get reader for clip 2, closing reader for clip 1.
        #     3. Attempt to read samples from reader for clip 1.
        #
        # Step 3 results in an exception since the reader for clip 1
        # was closed in step 2.
        
        with self._read_lock:
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
