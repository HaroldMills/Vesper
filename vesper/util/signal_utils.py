"""Utility functions pertaining to signals."""


import datetime

import scipy.signal as signal

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


def resample(sound, target_sample_rate):
    
    """
    Resamples a sound to a specified sample rate.
    
    This function should only be used for relatively short sounds, say not
    longer than a second or so. It uses the `scipy.signal.resample` method
    to perform the resampling, which computes a length-M DFT and a length-N
    inverse DFT, where M and N are the input and output length, respectively.
    M and N may not be powers of two, and they may even be prime, which can
    make this function slow if M or N is too large.
    """
    
    
    if sound.sample_rate == target_sample_rate:
        # do not need to resample
        
        return sound
    
    else:
        # need to resample
        
        ratio = target_sample_rate / sound.sample_rate
        num_samples = int(round(len(sound.samples) * ratio))
        samples = signal.resample(sound.samples, num_samples)
        return Bunch(samples=samples, sample_rate=target_sample_rate)
    