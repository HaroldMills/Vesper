"""Module containing `SampleBuffer` class."""


from collections import deque

import numpy as np


class SampleBuffer:
    
    """
    FIFO sample buffer.
    
    A `SampleBuffer` decouples sample production from sample consumption,
    enabling a producer and a consumer to write and read samples in
    whatever way is most convenient for them.
    
    A *sample producer* writes a sequence of NumPy sample arrays to a
    `SampleBuffer` via the buffer's `write` method. The arrays can be of
    various sizes. The buffer retains samples written by the producer
    until the consumer indicates (by incrementing the buffer's read index:
    see below) that it no longer needs them.
    
    A *sample consumer* reads the samples written by the producer via
    the buffer's `read` method. Each call to the `read` method returns
    one NumPy sample array. The consumer can read different numbers of
    samples in different `read` calls, and the read sizes are independent
    of the producer's write sizes. Each read starts at the *read index*
    of the buffer. The read index starts at zero and is incremented by
    the consumer, either via the `read` method or via the separate
    `increment` method. The only constraint on the read index is that
    it cannot be decremented: it can only be incremented or left
    unchanged. By controlling the read index appropriately, the
    consumer can read consecutive, overlapping, or non-consecutive and
    non-overlapping sample arrays.
    """
    
    
    def __init__(self, dtype):
        
        """
        Initializes this buffer.
        
        The buffer is empty after initialization, with a write index,
        read index, and length of zero.
        
        Parameters
        ----------
        dtype : NumPy dtype
            the `dtype` of this buffer.
        """
        
        self._dtype = np.dtype(dtype)
        self._arrays = deque()
        self._stored_start_index = 0
        self._stored_length = 0
        self._read_index = 0
        
        
    @property
    def dtype(self):
        return self._dtype
    
    
    @property
    def _stored_end_index(self):
        return self._stored_start_index + self._stored_length
    
    
    @property
    def write_index(self):
        return self._stored_end_index
    
    
    @property
    def read_index(self):
        return self._read_index
    
    
    def __len__(self):
        return max(self._stored_end_index - self._read_index, 0)
    
    
    def write(self, samples):
        
        """
        Writes the specified samples to this buffer.
        
        Parameters
        ----------
        samples : NumPy array
            the samples to be written.
            
            The sample array should not be modified after writing
            until the buffer's read index has been incremented past it.
            
        Raises
        ------
        ValueError
            if the `dtype` of `samples` differs from that of this buffer.
        """
        
        
        if samples.dtype != self._dtype:
            
            raise ValueError((
                'NumPy dtype "{}" of samples does not match sample '
                'buffer dtype "{}".').format(
                    str(samples.dtype), str(self._dtype)))
            
        else:
            # `samples` dtype matches buffer dtype
            
            if len(samples) != 0:
                self._arrays.append(samples)
                self._stored_length += len(samples)
        
        
    def read(self, num_samples=None, increment=None):
        
        """
        Reads samples from this buffer.
        
        Parameters
        ----------
        num_samples : int or None
            the number of samples to read, or `None` to read all available
            samples.
            
        increment : int or None
            the number by which to increment the read index of this buffer,
            or `None` to increment it by `num_samples`.
            
        Returns
        -------
        NumPy array of samples, of this buffer's `dtype`.
        
        Raises
        ------
        ValueError
            if `num_samples` or `increment` is negative, or if `num_samples`
            exceeds the current buffer length.
        """
        
        if num_samples is None:
            num_samples = len(self)
            
        elif num_samples < 0:
            raise ValueError('Sample buffer read size cannot be negative.')
        
        elif num_samples > len(self):
            raise ValueError((
                'Attempt to read {} samples from sample buffer with '
                'only {}.').format(num_samples, len(self)))
        
        if increment is None:
            increment = num_samples
            
        elif increment < 0:
            raise ValueError(
                'Sample buffer read increment cannot be negative.')

        if num_samples == 0:
            result = np.array([], dtype=self._dtype)
        
        else:
            # num_samples is positive
            
            result_arrays = []
            array_num = 0
            start = self.read_index - self._stored_start_index
            n = num_samples
            
            while n != 0:
                
                array = self._arrays[array_num]
                length = len(array)
                available = length - start
                
                if n >= available:
                    # result will include rest of `array`
                    
                    result_arrays.append(array[start:])
                    array_num += 1
                    start = 0
                    n -= available
    
                else:
                    # result will include only part of rest of `array`
                    
                    result_arrays.append(array[start:start + n])
                    n -= n
                    
            result = np.concatenate(result_arrays)
            
        if increment != 0:
            self.increment(increment)
            
        return result
        
        
    def increment(self, num_samples):
        
        """
        Increments the read index of this buffer.
        
        Parameters
        ----------
        num_samples : int
            the number of samples by which to increment the read index.
            
        Raises
        ------
        ValueError
            if `num_samples` is negative.
        """
        
        if num_samples < 0:
            raise ValueError(
                'Sample buffer read increment cannot be negative.')
            
        else:
            
            if num_samples >= len(self):
                # increment will skip over all available samples
                
                self._arrays.clear()
                self._stored_start_index = self._stored_end_index
                self._stored_length = 0
                
            else:
                # increment will not skip over all available samples
                
                start = self.read_index - self._stored_start_index
                n = num_samples
                
                while n != 0:
                    
                    length = len(self._arrays[0])
                    available = length - start
                    
                    if n >= available:
                        # increment will skip over rest of `array`
                        
                        self._arrays.popleft()
                        self._stored_start_index += length
                        self._stored_length -= length
                        start = 0
                        n -= available
                        
                    else:
                        # increment will skip over only part of rest of `array`
                        
                        n -= n
                    
            self._read_index += num_samples
