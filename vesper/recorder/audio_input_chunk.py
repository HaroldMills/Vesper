"""Module containing audio input chunk classes."""


import numpy as np

from vesper.recorder.audio_sample_format import AUDIO_SAMPLE_FORMATS


_OUTPUT_SAMPLE_DTYPE = np.dtype('float32')


# TODO: Implement `Int24AudioInputChunk`.
# TODO: Implement `Float32AudioInputChunk`.


class AudioInputChunk:
    
    """
    Superclass of audio input chunks.

    An audio input chunk is a buffer to which one can write 1-D byte
    arrays of raw audio input data (e.g. as they arrive from a
    `RawInputStream` of the Python `sounddevice` package) and then
    read the data as 2-D NumPy arrays of normalized float32 samples.
    In the read data, the samples are normalized to the interval
    [-1, 1] regardless of the input sample type, e.g. int16, int24,
    or float32. The samples of different channels are also
    deinterleaved: the first index of the 2-D array is for channel
    and the second is for sample frame.

    There is a separate subclass of this class for each supported
    input sample type, including int16, int24, and float32.
    """


    input_sample_format = None
    """
    The input sample format of this chunk type, an `AudioSampleFormat`.
    """


    def __init__(self, channel_count, capacity, input_sample_dtype):
        
        self._channel_count = channel_count
        self._capacity = capacity

        self._input_sample_dtype = np.dtype(input_sample_dtype)
        """
        The NumPy dtype of stored input samples.

        Note that this dtype can differ in size from
        `input_sample_format.size`. For example, for 24-bit integer
        samples `input_sample_format.size` is 3 bytes while
        `input_sample_dtype` is `int32`, where int32 array elements
        each take 4 bytes of storage.
        """

        self._input_frame_size = \
            self._channel_count * self._input_sample_dtype.itemsize
        
        self._create_buffers()

        self._sample_scale_factor = 1 / self.input_sample_format.max_abs_sample
        
        self._size = 0


    def _create_buffers(self):

        """
        Creates the sample buffers for this chunk.

        Subclasses can override this method if they need to create
        different or additional buffers.
        """

        # Create `bytearray` for input sample bytes.
        self._input_bytes = bytearray(self._capacity * self._input_frame_size)

        # Create 1-D NumPy array backed by `self._input_bytes` with sample
        # dtype.
        input_samples = \
            np.frombuffer(self._input_bytes, self._input_sample_dtype)
        
        # Create 2-D view of array with shape
        # `(self._capacity, self._channel_count)`.
        input_samples = \
            input_samples.reshape(self._capacity, self._channel_count)

        # Create transposed version of 2-D view, i.e. with shape
        # `(self._channel_count, self._capacity)`.
        self._input_samples = input_samples.transpose()

        # Create Numpy array with output sample dtype and shape
        # `(self._channel_count, self._capacity)`.
        shape = (self._channel_count, self._capacity)
        self._output_samples = np.empty(shape, _OUTPUT_SAMPLE_DTYPE)
    

    @property
    def channel_count(self):
        return self._channel_count
    

    @property
    def capacity(self):
        return self._capacity
    

    @property
    def sample_format(self):
        return self._sample_format
    

    @property
    def size(self):
        return self._size
    

    def clear(self):
        self._size = 0


    def write(self, input_bytes, start_frame_num=0, frame_count=None):

        start_index = start_frame_num * self._input_frame_size

        if frame_count is None:
            frame_count = \
                (len(input_bytes) - start_index) // self._input_frame_size

        remaining = self._capacity - self._size
        write_size = min(frame_count, remaining)

        self._write(input_bytes, start_index, write_size)
        self._size += write_size

        return write_size
    

    def _write(self, input_bytes, start_index, frame_count):
        copy_size = frame_count * self._input_frame_size
        read_end_index = start_index + copy_size
        write_start_index = self._size * self._input_frame_size
        write_end_index = write_start_index + copy_size
        self._input_bytes[write_start_index:write_end_index] = \
            input_bytes[start_index:read_end_index]
        
    
    @property
    def samples(self):

        """
        The samples of this chunk, in a float32 NumPy array.

        The samples are returned as a float32 NumPy array with shape
        `(self.channel_count, self.size)`. The samples are normalized
        to the range [-1, 1] and are stored in C-like order.
        """

        size = self._size
        output_samples = self._output_samples[:, :size]

        # Copy input samples into output sample array. Note that the
        # copy will perform any needed sample type conversion, and
        # the output samples will be in C-like order even if the
        # input samples are not.
        output_samples[:, :] = self._input_samples[:, :size]

        # Scale samples if needed.
        if self._sample_scale_factor is not None:
            output_samples *= self._sample_scale_factor

        return output_samples


class Int16AudioInputChunk(AudioInputChunk):


    """Audio input chunk for int16 samples."""


    input_sample_format = AUDIO_SAMPLE_FORMATS['int16']
    

    def __init__(self, channel_count, capacity):
        super().__init__(channel_count, capacity, 'int16')


AUDIO_INPUT_CHUNK_TYPES = {
    t.input_sample_format.name: t for t in (Int16AudioInputChunk,)
}
