from collections import deque
import threading

from vesper.util.decorators import synchronized


class AudioInputBufferOverflow(Exception):

    def __init__(self, overflow_size):

        super().__init__(
            f'Audio input buffer discarded {overflow_size} frames of '
            f'input data due to overflow.')
        
        self.overflow_size = overflow_size


class AudioInputBuffer:


    """
    Chunked audio input buffer.

    Writes to the buffer can be of various sizes, but reads are always
    of one size, the *chunk size*.
    """


    def __init__(self, channel_count, capacity, chunk_size, chunk_type):
        self._channel_count = channel_count
        self._capacity = capacity
        self._chunk_size = chunk_size
        self._chunk_type = chunk_type
        sample_size = chunk_type.input_sample_format.sample_size
        self._sample_frame_size = self._channel_count * sample_size
        self._lock = threading.Lock()
        self.clear()


    @property
    def channel_count(self):
        """the channel count of this buffer."""
        return self._channel_count
    

    @property
    def capacity(self):
        """the capacity of this buffer, in chunks."""
        return self._capacity
    

    @property
    def chunk_size(self):
        """the chunk size of this buffer, in sample frames."""
        return self._chunk_size
    

    @property
    def chunk_type(self):
        """the chunk type of this buffer, an `AudioInputChunk` subclass."""
        return self._chunk_type
    

    @property
    @synchronized
    def size(self):
        """the current size of this buffer, in filled chunks."""
        return len(self._full_chunks)
    

    @synchronized
    def clear(self):
        self._empty_chunks = self._create_chunks()
        self._write_chunk = None
        self._full_chunks = deque()


    def _create_chunks(self):

        """Creates the chunks of this buffer and returns them in a list."""

        return [
            self._chunk_type(self._channel_count, self._chunk_size)
            for _ in range(self._capacity)]
   

    @synchronized
    def write(self, data, size=None):

        if size == 0:
            return
        
        start_frame_num = 0

        if size is None:
            remaining = len(data) // self._sample_frame_size
        else:
            remaining = size

        while remaining != 0:

            # Get a new write chunk if needed. Note that we detect input
            # overflow when we need to write to a new chunk but none is
            # available. Thus input overflow only occurs at chunk
            # boundaries, and when it occurs we drop the data that would
            # have been written to the unavailable chunk or chunks.
            if self._write_chunk is None:
                try:
                    self._write_chunk = self._empty_chunks.pop()
                except IndexError:
                    raise AudioInputBufferOverflow(remaining)
                
            chunk = self._write_chunk
                
            written = chunk.write(data, start_frame_num, remaining)

            if chunk.size == chunk.capacity:
                # write chunk full

                self._full_chunks.append(chunk)
                self._write_chunk = None

            start_frame_num += written
            remaining -= written


    @synchronized
    def get_chunk(self):
        try:
            return self._full_chunks.popleft()
        except IndexError:
            return None
   

    @synchronized
    def free_chunk(self, chunk):
        chunk.clear()
        self._empty_chunks.append(chunk)
