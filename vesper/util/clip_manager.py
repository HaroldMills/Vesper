"""Module containing `ClipManager` class."""


from io import BytesIO
from threading import Lock
import asyncio
import os.path

from environs import Env
import aioboto3
import numpy as np

from vesper.archive_paths import archive_paths
from vesper.signal.wave_file_signal import WaveFileSignal
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
        self._recording_channel_info_cache = {}
        self._recording_info_cache = {}
        self._recording_file_signal_cache = {}
        self._read_lock = Lock()
        
        # Get S3 clip info, if present.
        env = Env()
        self._aws_access_key_id = env('VESPER_AWS_ACCESS_KEY_ID', None)
        self._aws_secret_access_key = env('VESPER_AWS_SECRET_ACCESS_KEY', None)
        self._aws_region_name = env('VESPER_AWS_REGION_NAME', None)
        self._aws_s3_clip_bucket_name = \
            env('VESPER_AWS_S3_CLIP_BUCKET_NAME', None)
        self._aws_s3_clip_folder_path = \
            env('VESPER_AWS_S3_CLIP_FOLDER_PATH', None)
        
        # Make sure non-`None` clip folder path ends with "/".
        if self._aws_s3_clip_folder_path is not None and \
                not self._aws_s3_clip_folder_path.endswith('/'):
            self._aws_s3_clip_folder_path += '/'


    def get_audio_file_path(self, clip):
        return _get_audio_file_path(clip.id)
    
        
    def has_audio_file(self, clip):
        path = self.get_audio_file_path(clip)
        return os.path.exists(path)
        
    
    def get_audio(self, clip):
        samples = self.get_samples(clip)
        sample_rate = clip.sample_rate
        return Bunch(samples=samples, sample_rate=sample_rate)
    
    
    def get_samples(self, clip, start_offset=0, length=None):
        
        """
        Gets samples of the specified clip.
        
        The samples are read from the clip's audio file if there is one
        and it contains all of the specified samples, or from the clip's
        recording otherwise.
        
        Parameters
        ----------
        clip : Clip
            the clip for which to get samples.
            
        start_offset : int
            offset from the start of the specified clip of the samples to
            get.
            
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
        
        length = _get_clip_time_interval_length(clip, start_offset, length)

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


    def _get_samples_from_recording(self, clip, start_offset=0, length=None):
        
        if clip.start_index is None:
            # have no clip start index
            
            self._handle_get_samples_error('Clip start index is not known.')
        
        else:
            # have clip start index
            
            try:
                recording_files, channel_num, start_index, end_index = \
                    self.get_recording_file_info(clip, start_offset, length)
            except ClipManagerError as e:
                self._handle_get_samples_error(str(e))
            
            samples = self._get_samples_from_recording_files(
                recording_files, channel_num, start_index, end_index)
            
            return samples
    
    
    def _handle_get_samples_error(self, message):
        raise ClipManagerError(
            f'Could not get clip samples from recording audio files. '
            f'{message}')
    
    
    def get_recording_file_info(self, clip, start_offset=0, length=None):
        
        length = _get_clip_time_interval_length(clip, start_offset, length)
        
        start_index = clip.start_index + start_offset
        end_index = start_index + length
        
        files, file_bounds, channel_num = \
            self._get_recording_file_info_aux(clip)
        
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
        
        return files, channel_num, start_index, end_index
    
    
    def _get_recording_file_info_aux(self, clip):
        
        try:
            recording_id, channel_num = \
                self._recording_channel_info_cache[clip.recording_channel_id]
        
        except KeyError:
            channel = clip.recording_channel
            recording_id = channel.recording_id
            channel_num = channel.channel_num
            self._recording_channel_info_cache[channel.id] = \
                recording_id, channel_num
        
        try:
            files, bounds = self._recording_info_cache[recording_id]
        
        except KeyError:
            files = list(clip.recording.files.all())
            bounds = [f.start_index for f in files]
            if len(files) != 0:
                bounds.append(bounds[-1] + files[-1].length)
            self._recording_info_cache[recording_id] = files, bounds
        
        return files, bounds, channel_num
    
    
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
        
        # Since the file signal cache may be shared among threads, we
        # use a lock to make getting a file signal for a clip and reading
        # samples from it atomic.
        #
        # Without the lock, we have observed that reads can return the
        # wrong samples. For example, suppose that this method is called
        # on separate threads for two different clips, clips 1 and 2,
        # that are in the same file and hence will use the same file
        # signal. We want the seek and read operations for the two clips
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
        # If we don't make the combination of getting the file signal
        # for a clip and reading from the signal atomic, the following
        # can happen when we try to read two clips whose samples are in
        # different files:
        #
        #     1. Get signal for clip 1.
        #     2. Get signal for clip 2, closing signal for clip 1.
        #     3. Attempt to read samples from signal for clip 1.
        #
        # Step 3 results in an exception since the signal for clip 1
        # was closed in step 2.
        
        with self._read_lock:
            signal = self._get_recording_file_signal(path)
            channel = signal.channels[channel_num]
            return channel.read(start_index, length)
    
    
    def _get_recording_file_signal(self, path):
        
        try:
            signal = self._recording_file_signal_cache[path]
        
        except KeyError:
            # cache miss
            
            # Clear cache. We cache just one signal at a time, which
            # goes a long way since in typical use our accesses don't
            # switch files very often.
            self._clear_recording_file_signal_cache()
            
            # Create new signal.
            signal = WaveFileSignal(path)
            
            # Cache new signal.
            self._recording_file_signal_cache[path] = signal
            
        return signal
    
    
    def _clear_recording_file_signal_cache(self):
        
        for signal in self._recording_file_signal_cache.values():
            signal.close()
            
        self._recording_file_signal_cache = {}
    
    
    def get_audio_file_contents(self, clips):

        if self._aws_s3_clip_bucket_name is not None:

            return self._get_s3_audio_file_contents(clips)

        else:
            # using file system clip storage

            return self._get_audio_file_contents(clips)
        

    def _get_s3_audio_file_contents(self, clips):

        # Get clip IDs. We must do this before calling asynchronous code
        # since Django will raise a `SynchronousOnlyOperation` exception
        # if we try to perform database operations in an asynchronous
        # function.
        clip_ids = [clip.id for clip in clips]

        return asyncio.run(self._get_s3_audio_file_contents_async(clip_ids))
    

    async def _get_s3_audio_file_contents_async(self, clip_ids):

        object_keys = [
            self._get_s3_audio_file_object_key(i)
            for i in clip_ids]

        session = aioboto3.Session(
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            region_name=self._aws_region_name)
        
        async with session.resource('s3') as s3:
            coroutines = [
                self._get_s3_audio_file_contents_aux(s3, object_key)
                for object_key in object_keys]
            return await asyncio.gather(*coroutines)


    def _get_s3_audio_file_object_key(self, i):

        parts = []

        # Include clip folder path if and only if it isn't `None`
        if self._aws_s3_clip_folder_path is not None:
            parts.append(self._aws_s3_clip_folder_path[:-1])

        parts += _get_relative_audio_file_path_parts(i)

        # Since we're creating an S3 object key, we use "/" as the
        # path component separator regardless of which platform we're
        # running on.
        return '/'.join(parts)


    async def _get_s3_audio_file_contents_aux(self, s3, object_key):
        obj = await s3.Object(self._aws_s3_clip_bucket_name, object_key)
        result = await obj.get()
        body = result['Body']
        data = await body.read()
        return data


    def _get_audio_file_contents(self, clips):
        return [self._get_audio_file_contents_aux(clip) for clip in clips]
            

    def _get_audio_file_contents_aux(self, clip):
        
        try:

            try:
                return self._get_audio_file_contents_from_audio_file(clip)
                
            except FileNotFoundError:
                return self._get_audio_file_contents_from_recording(clip)
            
        except Exception as e:
            raise ClipManagerError(
                f'Attempt to get audio file contents for clip '
                f'"{str(clip)}" failed with {e.__class__.__name__} '
                f'exception. Exception message was: {e}')
            
            
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


    def export_audio_file(self, clip, path, start_offset=0, length=None):
        
        """
        Exports an audio file for the specified clip.
        
        If the file already exists, it is overwritten.
        
        Parameters
        ----------
        clip : Clip
            the clip to export.
            
        path : str
            the path of the audio file to create.

        start_offset : int
            export start offset in samples after clip start.

        length : int or None
            export length in samples, or `None` to export through the
            end of the clip.
        """
        
        samples = self.get_samples(clip, start_offset, length)
        self._create_audio_file(clip, samples, path)        
        
        
def _get_audio_file_path(clip_id):
    relative_path = _get_relative_audio_file_path(clip_id)
    # print(f'clip_manager._get_audio_file_path "{relative_path}"')
    return os.path.join(str(archive_paths.clip_dir_path), relative_path)


_CLIPS_DIR_FORMAT = (3, 3, 3)


def _get_relative_audio_file_path(clip_id):
    path_parts = _get_relative_audio_file_path_parts(clip_id)
    return os.path.join(*path_parts)


def _get_relative_audio_file_path_parts(clip_id):
    id_parts = _get_clip_id_parts(clip_id, _CLIPS_DIR_FORMAT)
    path_parts = id_parts[:-1]
    id_ = ' '.join(id_parts)
    file_name = 'Clip {}.wav'.format(id_)
    path_parts.append(file_name)
    return path_parts


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
    
    
def _get_clip_time_interval_length(clip, start_offset, length):
    
    if length is None:
        length = max(clip.length - start_offset, 0)
        
    return length
            

def _create_audio_file_contents(samples, sample_rate):
    
    buffer = BytesIO()
    
    # Get 2-D version of `samples` for call to
    # `audio_file_utils.write_wave_file`.
    # TODO: Enhance `audio_file_utils.write_wave_file` to obviate this.
    samples = samples.reshape((1, samples.size))
    
    audio_file_utils.write_wave_file(buffer, samples, sample_rate)
    
    return buffer.getvalue()
