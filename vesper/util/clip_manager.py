"""Module containing `ClipManager` class."""


from io import BytesIO
from threading import Lock
import os.path

import numpy as np

from vesper.archive_paths import archive_paths
from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.singleton.recording_manager import recording_manager
from vesper.util.bunch import Bunch
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils


class ClipManagerError(Exception):
    pass


class ClipManager:
    
    """Gets the audio data of the clips of a Vesper archive."""
    
    
    def __init__(self):
        self._rm = recording_manager
        self._recording_file_info_cache = {}
        self._recording_file_reader_cache = {}
        self._read_lock = Lock()
        
        
    def get_audio_file_path(self, clip):
        return _get_audio_file_path(clip.id)
    
        
    def has_audio_file(self, clip):
        path = self.get_audio_file_path(clip)
        return os.path.exists(path)
        
    
    def get_audio(self, clip):
        samples = self.get_samples(clip)
        sample_rate = clip.sample_rate
        return Bunch(samples=samples, sample_rate=sample_rate)
    
    
    def get_samples(self, clip, start_offset=None, length=None):
        
        """
        Gets samples of the specified clip.
        
        The samples are read from the clip's audio file if there is one
        and it contains all of the specified samples, or from the clip's
        recording otherwise.
        
        Parameters
        ----------
        clip : Clip
            the clip for which to get samples.
            
        start_offset : int or None
            offset from the start of the specified clip of the samples to
            get, or `None` to get samples from the start of the clip.
            
        length : int or None
            the number of samples to get, or `None` to get samples through
            the end of the clip.
            
        Returns
        -------
        NumPy array
            the specified samples.
        
        Raises
        ------
        ClipManagerError
            If one of a certain set of error conditions occurs, for
            example if neither a clip audio file or recording file
            can be located for the specified clip.
            
        Exception
            If some other error occurs, for example a file I/O error.
        """
        
        start_offset, length = \
            _complete_clip_segment_spec(clip, start_offset, length)

        if start_offset >= 0 and start_offset + length <= clip.length:
            # all requested samples are in clip audio file if it exists
            
            try:
                return self._get_samples_from_audio_file(
                    clip, start_offset, length)
                
            except FileNotFoundError:
                # clip audio file does not exist
                
                return self._get_samples_from_recording(
                    clip, start_offset, length)
                
        else:
            # some requested samples would not be in clip audio file
            
            return self._get_samples_from_recording(clip, start_offset, length)
            
       
    def _get_samples_from_audio_file(self, clip, start_index, length):
        path = self.get_audio_file_path(clip)
        samples, _ = audio_file_utils.read_wave_file(path)
        end_index = start_index + length
        return samples[0, start_index:end_index]


    def _get_samples_from_recording(
            self, clip, start_offset=None, length=None):
        
        if clip.start_index is None:
            # have no clip start index
            
            self._handle_get_samples_error('Clip start index is not known.')
        
        else:
            # have clip start index
            
            try:
                recording_files, start_index, end_index = \
                    self.get_recording_file_info(clip, start_offset, length)
            except ClipManagerError as e:
                self._handle_get_samples_error(str(e))
            
            samples = self._get_samples_from_recording_files(
                recording_files, clip.channel_num, start_index, end_index)
            
            return samples
    
    
    def _handle_get_samples_error(self, message):
        raise ClipManagerError(
            f'Could not get clip samples from recording audio files. '
            f'{message}')
    
    
    def get_recording_file_info(self, clip, start_offset=None, length=None):
        
        start_offset, length = \
            _complete_clip_segment_spec(clip, start_offset, length)
        
        start_index = clip.start_index + start_offset
        end_index = start_index + length
        
        files, file_bounds = self._get_recording_file_info_aux(clip)
        
        if len(files) == 0:
            raise ClipManagerError('Recording has no audio files.')
        
        start_file_num, start_index, end_file_num, end_index = \
            signal_utils.get_concatenated_signal_read_data(
                file_bounds, start_index, end_index)
        
        if start_file_num == -1:
            raise ClipManagerError('Clip starts before recording.')
        
        elif end_file_num == len(files):
            raise ClipManagerError('Clip ends after recording.')
            
        files = files[start_file_num:end_file_num + 1]
        
        return files, start_index, end_index
    
    
    def _get_recording_file_info_aux(self, clip):
        
        recording = clip.recording_channel.recording
        
        try:
            return self._recording_file_info_cache[recording.id]
        
        except KeyError:
            files = list(clip.recording.files.all())
            bounds = [f.start_index for f in files]
            if len(files) != 0:
                bounds.append(bounds[-1] + files[-1].length)
            result = (files, bounds)
            self._recording_file_info_cache[recording.id] = result
            return result
    
    
    def _get_samples_from_recording_files(
            self, files, channel_num, start_index, end_index):
        
        file_count = len(files)
        
        if file_count == 1:
            # reading from one file
             
            length = end_index - start_index
            return self._get_samples_from_recording_file(
                files[0], channel_num, start_index, length)
         
        else:
            # reading from more than one file
         
            file_samples = []
            
            for i, file_ in enumerate(files):
                
                # Get start and end indices for read from this file.
                start = start_index if i == 0 else 0
                end = end_index if i == file_count - 1 else file_.length
                
                # Read samples.
                length = end - start
                samples = self._get_samples_from_recording_file(
                    file_, channel_num, start, length)
                
                # Save samples.
                file_samples.append(samples)
            
            # Concatenate samples.
            samples = np.concatenate(file_samples)
            
            return samples
    
    
    def _get_samples_from_recording_file(
            self, file_, channel_num, start_index, length):
        
        try:
            path = self._rm.get_absolute_recording_file_path(file_.path)
            
        except ValueError as e:
            raise ClipManagerError((
                'Could not read clip samples from recording file. '
                '{}').format(str(e)))
        
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
            reader = self._get_recording_file_reader(path)
            samples = reader.read(start_index, length)
        
        return samples[channel_num]
    
    
    def _get_recording_file_reader(self, path):
        
        try:
            reader = self._recording_file_reader_cache[path]
        
        except KeyError:
            # cache miss
            
            # Clear cache. We cache just one reader at a time, which
            # goes a long way since in typical use our accesses don't
            # switch files very often.
            self._clear_recording_file_reader_cache()
            
            # Create new reader.
            reader = WaveAudioFileReader(str(path))
            
            # Cache new reader.
            self._recording_file_reader_cache[path] = reader
            
        return reader
    
    
    def _clear_recording_file_reader_cache(self):
        
        for reader in self._recording_file_reader_cache.values():
            reader.close()
            
        self._recording_file_reader_cache = {}
    
    
    def get_audio_file_contents(self, clip, media_type):
        
        if media_type != 'audio/wav':
            raise ValueError(
                'Unrecognized media type "{}".'.format(media_type))
            
        try:
            return self._get_audio_file_contents_from_audio_file(clip)
            
        except FileNotFoundError:
            return self._get_audio_file_contents_from_recording(clip)
            
            
    def _get_audio_file_contents_from_audio_file(self, clip):
        path = self.get_audio_file_path(clip)
        with open(path, 'rb') as file_:
            return file_.read()
        

    def _get_audio_file_contents_from_recording(self, clip):
        samples = self._get_samples_from_recording(clip)
        return _create_audio_file_contents(samples, clip.sample_rate)
            
            
    def delete_audio_file(self, clip):
        
        """
        Deletes the audio file of the specified clip.
        
        If the audio file is not present, this method does nothing.
        
        Parameters
        ----------
        clip : Clip
            the clip whose audio file should be deleted.
        """
        
        path = self.get_audio_file_path(clip)
        os_utils.delete_file(path)
        
            
    def create_audio_file(self, clip, samples=None):
        
        """
        Creates an audio file for the specified clip.

        If the audio file already exists, it is overwritten.
        
        Parameters
        ----------
        clip : Clip
            the clip for which to create an audio file.
            
        samples : NumPy array
            the clip's samples, or `None`.
            
            If this argument is `None`, the clip's samples are obtained
            from its recording.
        """
        
        if samples is None:
            samples = self._get_samples_from_recording(clip)
            
        self._create_audio_file(clip, samples)
        
        
    def _create_audio_file(self, clip, samples, path=None):
        
        # Get 2-D version of `samples` for call to
        # `audio_file_utils.write_wave_file`.
        # TODO: Enhance `audio_file_utils.write_wave_file` to obviate this.
        samples = samples.reshape((1, samples.size))
        
        if path is None:
            path = self.get_audio_file_path(clip)
            
        os_utils.create_parent_directory(path)
        
        audio_file_utils.write_wave_file(path, samples, clip.sample_rate)


    def export_audio_file(self, clip, path):
        
        """
        Exports an audio file for the specified clip.
        
        If the file already exists, it is overwritten.
        
        Parameters
        ----------
        clip : Clip
            the clip to export.
            
        path : str
            the path of the audio file to create.
        """
        
        samples = self.get_samples(clip)
        self._create_audio_file(clip, samples, path)        
        
        
_CLIPS_DIR_FORMAT = (3, 3, 3)


def _get_audio_file_path(clip_id):
    id_parts = _get_clip_id_parts(clip_id, _CLIPS_DIR_FORMAT)
    path_parts = id_parts[:-1]
    id_ = ' '.join(id_parts)
    file_name = 'Clip {}.wav'.format(id_)
    path_parts.append(file_name)
    return os.path.join(str(archive_paths.clip_dir_path), *path_parts)


def _get_clip_id_parts(num, format_):
    
    # Format number as digit string with leading zeros.
    num_digits = sum(format_)
    f = '{:0' + str(num_digits) + 'd}'
    digits = f.format(num)
    
    # Split string into parts.
    i = 0
    parts = []
    for num_digits in format_:
        parts.append(digits[i:i + num_digits])
        i += num_digits
        
    return parts
    
    
def _complete_clip_segment_spec(clip, start_offset, length):
    
    if start_offset is None:
        start_offset = 0
        
    if length is None:
        length = max(clip.length - start_offset, 0)
        
    return start_offset, length
            

def _create_audio_file_contents(samples, sample_rate):
    
    buffer = BytesIO()
    
    # Get 2-D version of `samples` for call to
    # `audio_file_utils.write_wave_file`.
    # TODO: Enhance `audio_file_utils.write_wave_file` to obviate this.
    samples = samples.reshape((1, samples.size))
    
    audio_file_utils.write_wave_file(buffer, samples, sample_rate)
    
    return buffer.getvalue()
