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


    def __init__(self, capacity, chunk_size, sample_frame_size):
        self._capacity = capacity
        self._chunk_size = chunk_size
        self._sample_frame_size = sample_frame_size
        self._lock = threading.Lock()
        self.clear()


    @property
    def capacity(self):
        """the capacity of this buffer, in chunks."""
        return self._capacity
    

    @property
    def chunk_size(self):
        """the chunk size of this buffer, in sample frames."""
        return self._chunk_size
    

    @property
    def sample_frame_size(self):
        """the sample frame size of this buffer, in bytes."""
        return self._sample_frame_size
    

    @property
    @synchronized
    def size(self):
        """the current size of this buffer, in filled chunks."""
        return len(self._full_chunks)
    

    @synchronized
    def clear(self):
        self._empty_chunks = self._create_chunks()
        self._write_chunk = None
        self._write_start_index = None
        self._full_chunks = deque()


    def _create_chunks(self):

        """Creates the chunks of this buffer and returns them in a list."""

        chunk_size = self._chunk_size * self._sample_frame_size
        return [bytearray(chunk_size) for _ in range(self._capacity)]
    

    @synchronized
    def write(self, data, size=None):

        if size == 0:
            return
        
        chunk_size = self._chunk_size * self._sample_frame_size

        if size is None:
            remaining = len(data)
        else:
            remaining = size * self._sample_frame_size

        read_start_index = 0
        
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
                    raise AudioInputBufferOverflow(
                        remaining // self._sample_frame_size)
                else:
                    self._write_start_index = 0
                
            chunk_remaining = chunk_size - self._write_start_index
            write_size = min(remaining, chunk_remaining)

            read_end_index = read_start_index + write_size
            write_end_index = self._write_start_index + write_size

            self._write_chunk[self._write_start_index:write_end_index] = \
                data[read_start_index:read_end_index]
            
            remaining -= write_size
            read_start_index = read_end_index
            self._write_start_index = write_end_index

            if self._write_start_index == chunk_size:
                # write chunk full

                self._full_chunks.append(self._write_chunk)
                self._write_chunk = None
                self._write_start_index = None


    @synchronized
    def get_chunk(self):
        try:
            return self._full_chunks.popleft()
        except IndexError:
            return None
   

    @synchronized
    def free_chunk(self, chunk):
        self._empty_chunks.append(chunk)
