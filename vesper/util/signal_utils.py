"""Utility functions pertaining to signals."""


import bisect
import datetime

import numpy as np

from vesper.util.bunch import Bunch


def seconds_to_frames(seconds, frame_rate):
    return int(round(seconds * frame_rate))


def get_duration(num_samples, sample_rate):
    
    """
    Gets the duration of some consecutive samples in seconds.
    
    The duration of consecutive samples is defined as the number of
    samples times the sample period.
    
    :Parameters:
    
        num_samples : nonnegative number
            the number of samples.
            
        sample_rate : positive number
            the sample rate in Hertz.
    """
    
    return num_samples / sample_rate


def get_span(num_samples, sample_rate):
    
    """
    Gets the span of some consecutive samples in seconds.
    
    The *span* of consecutive samples is defined as the time elapsed
    from the first sample to the last sample. The span of zero samples
    is defined to be zero.
    
    :Parameters:
    
        num_samples : nonnegative number
            the number of samples.
            
        sample_rate : positive number
            the sample rate in Hertz.
    """
    
    if num_samples == 0:
        return 0
    else:
        return (num_samples - 1) / sample_rate


def get_end_time(start_time, num_samples, sample_rate):
    
    """
    Gets the end time of some consecutive samples.
    
    The end time of consecutive samples is defined as the start
    time of the samples plus the span of the samples.
    
    :Parameters:
    
        start_time : datetime
            the time of the first sample.
            
        num_samples : nonnegative number
            the number of samples.
            
        sample_rate : positive number
            the sample rate in hertz.
    """
    
    span = get_span(num_samples, sample_rate)
    return start_time + datetime.timedelta(seconds=span)


def get_concatenated_signal_read_data(segment_bounds, start_index, end_index):
    
    """
    Gets read interval index data for a concatenated signal.
    
    Given an index range for a concatenated signal, this function
    returns the corresponding start and end (segment_num, segment_index)
    pairs.
    
    Parameters
    ----------
    
    segment_bounds : int sequence
        concatenated signal indices of segment boundaries.
        
        The length of this sequence must be one more than the number of
        segments in the concatenated signal. The ith element of the
        sequence must be the sum of the lengths of segments zero through i.
    
    start_index : int
        read interval start index in concatenated signal
        
        This parameter can be less than zero or greater than the
        concatenated signal length.
    
    end_index : int
        read interval end index in concatenated signal
        
        This parameter can be less than zero or greater than the
        concatenated signal length.
    
    Returns
    -------
    
    start_segment_num : int
        the number of the signal segment that includes the start of
        the read interval.
        
        If the read interval is empty, this return value is zero.
        Otherwise, it is -1 if the read interval start index is
        negative, or the number of signal segments if the read
        interval start index is greater than the concatenated
        signal length.
    
    start_segment_index : int
        the index within segment `start_segment_num` of the start of
        the read interval.
        
        If the read interval is empty, this return value is zero.
        Otherwise, it will be negative if `start_segment_num` is -1,
        indicating a number of sample frames prior to the start of
        the signal, or nonnegative if `start_segment_num` is
        nonnegative.
    
    end_segment_num : int
        the number of the signal segment that includes the end of
        the read interval.
        
        If the read interval is empty, this return value is zero.
        Otherwise, it is -1 if the read interval end index is
        negative, or the number of signal segments if the read
        interval end index is greater than the concatenated
        signal length.
    
    end_segment_index : int
        the index within segment `end_segment_num` of the end of
        the read interval.
        
        If the read interval is empty, this return value is zero.
        Otherwise, it will be negative if `end_segment_num` is -1,
        indicating a number of sample frames prior to the start of
        the signal, or nonnegative if `end_segment_num` is
        nonnegative.
    """
    
    if start_index >= end_index:
        # read interval empty
        
        return 0, 0, 0, 0
    
    else:
        # read interval not empty
        
        start_segment_num, start_index = \
            get_concatenated_signal_index_data(segment_bounds, start_index)
        
        end_segment_num, end_index = \
            get_concatenated_signal_index_data(segment_bounds, end_index)
        
        if end_index == 0 and end_segment_num > 0:
            # last sample to be read is the last sample of an actual segment
            
            # Replace end segment number and end index with equivalents
            # for preceding segment.
            end_segment_num -= 1
            i = end_segment_num
            end_index = segment_bounds[i + 1] - segment_bounds[i]
        
        return start_segment_num, start_index, end_segment_num, end_index


def get_concatenated_signal_index_data(segment_bounds, index):
    
    """
    Gets time index data for a concatenated signal.
    
    Given an index in the concatenated signal, this function returns
    the corresponding segment number and segment index.
    
    Parameters
    ----------
    
    segment_bounds : int sequence
        concatenated signal indices of segment boundaries.
        
        The length of this sequence must be one more than the number of
        segments in the concatenated signal. The ith element of the
        sequence must be the sum of the lengths of segments zero through i.
    
    index : int
        concatenated signal index.
        
        This parameter can be less than zero or greater than the
        concatenated signal length.
    
    Returns
    -------
    
    segment_num : int
        the number of the signal segment that includes the specified signal
        index.
        
        This return value will be -1 if the specified index is negative,
        or the number of signal segments if the specified index is greater
        than the concatenated signal length.
    
    segment_index : int
        the index within segment `segment_num` of the specified signal index.
        
        This return value will be negative if `segment_num` is -1,
        indicating a number of sample frames prior to the start of the
        signal. Otherwise it will be nonnegative.
    """
    
    if index < 0:
        # index prior to signal start
        
        return -1, index
    
    else:
        # index not prior to signal start
        
        segment_num = bisect.bisect_right(segment_bounds, index) - 1
        segment_index = index - segment_bounds[segment_num]
        return segment_num, segment_index


def find_samples(x, y, tolerance=0):
    
    """
    Finds all occurrences of one one-dimensional array in another.
    
    The algorithm employed by this function is efficient when there are
    few occurrences of a small prefix of the first array in the second.
    It is inefficient in other cases.
    
    Parameters
    ----------
    x : one-dimensional NumPy array
        the array to be searched for.
    y : one-dimensional NumPy array
        the array to be searched in.
            
    Returns
    -------
    NumPy array
        the starting indices of all occurrences of `x` in `y`.
    """

    m = len(x)
    n = len(y)
    
    if m == 0:
        return np.arange(n)
    
    else:
        # x has at least one element
        
        # Find indices i of x[0] in y[:n - m + 1]. These are the indices in y
        # where matches of x might start.
        diffs = np.abs(y[:n - m + 1] - x[0])
        i = np.where(diffs <= tolerance)[0]
        
        for k in range(1, m):
            # loop invariant: matches of x[:k] start at indices i in y
            
            if len(i) <= 1:
                # zero or one matches of x[:k] in y
                
                break
            
            # Find indices j of x[k] in y[i + k]. These are the indices
            # in i of the indices in y where matches of x[:k + 1] start. 
            diffs = np.abs(y[i + k] - x[k])
            j = np.where(diffs <= tolerance)[0]
            
            i = i[j]
        
        if len(i) == 1:
            # might have looked for only initial portion of x
            
            p = i[0]
            diffs = np.abs(y[p:p + m] - x)
            if np.all(diffs <= tolerance):
                return i
            else:
                return np.array([], dtype='int64')
        
        else:
            # i is the answer (it may have length zero, one, or more)
            
            return i


def find_peaks(x, min_value=None):
    
    """
    Finds peaks of the specified array.
    
    A *peak* of an array is an element that is greater than its neighbors
    on either side. Note that this means that the first and last elements
    of an array are not peaks, since neither has neighbors on both sides.
    It also means that no element of a sequence of equal elements is a peak.
    
    Parameters
    ----------
    x : one-dimensional NumPy array
        the array in which to find peaks.
    min_value : int, float, or None
        the minimum value of a peak, or `None` to find all peaks.
        
    Returns
    -------
    NumPy array
        indices in `x` of the specified peaks.
    """
    
    if len(x) < 3:
        # not enough elements for there to be any local maxima
        
        return np.array([], dtype='int32')
    
    else:
        # have enough elements for there to be local maxima
        
        x0 = x[:-2]
        x1 = x[1:-1]
        x2 = x[2:]
        
        indices = np.where((x0 < x1) & (x1 > x2))[0] + 1
        
        if min_value is not None:
            values = x[indices]
            keep_indices = np.where(values >= min_value)
            indices = indices[keep_indices]
            
        return indices
        
        
def resample(audio, target_sample_rate):
    
    """
    Resamples audio to a specified sample rate.
    
    This function should only be used for relatively short audio segments,
    say not longer than a second or so. It uses the `scipy.signal.resample`
    method to perform the resampling, which computes a length-M DFT and a
    length-N inverse DFT, where M and N are the input and output length,
    respectively. M and N may not be powers of two, and they may even be
    prime, which can make this function slow if M or N is too large.
    """
    
    
    if audio.sample_rate == target_sample_rate:
        # do not need to resample
        
        return audio
    
    else:
        # need to resample
        
        # We put this import here instead of at the top of this module
        # so  the module can be used in Python environments that don't
        # include SciPy as long as this function is not called.
        import scipy.signal as signal

        ratio = target_sample_rate / audio.sample_rate
        num_samples = int(round(len(audio.samples) * ratio))
        samples = signal.resample(audio.samples, num_samples)
        return Bunch(samples=samples, sample_rate=target_sample_rate)
