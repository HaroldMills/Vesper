"""NFC classification utility functions."""


import numpy as np

from vesper.util.spectrogram import Spectrogram


def get_segment_features(segment, config):
    
    c = config
    
    spectrogram = Spectrogram(segment, c.spectrogram_params)
    spectra = spectrogram.spectra
    
    # Clip spectra to specified power range.
    spectra.clip(config.min_power, config.max_power)
    
    # Remove portions of spectra outside of specified frequency range.
    sample_rate = segment.sample_rate
    dft_size = c.spectrogram_params.dft_size
    start_index = _freq_to_index(c.min_freq, sample_rate, dft_size)
    end_index = _freq_to_index(c.max_freq, sample_rate, dft_size) + 1
    spectra = spectra[:, start_index:end_index]
    
    # TODO: Should summing happen before logs are taken?
    # TODO: Consider parameterizing the pooling operation, and offering
    # at least averaging and max.
    spectra = _sum_adjacent(spectra, c.pooling_block_size)
    
    # TODO: Make each signal processing operation produce a correct time
    # calibration for each of its outputs, calculated according to the
    # time calibrations of its inputs and the signal processing operation
    # performed. Support both seconds and date/time calibrations.
    #
    # A small number of utility functions that perform time calibration
    # transformations should cover the vast majority of cases.
    #
    # It may be advantageous to maintain the date/time portion of
    # calibrations separately from the seconds portions. For example,
    # a calibration might comprise a start offset in seconds (zero by
    # default), a frame rate in frames per second (one by default),
    # and a start date/time (none by default). Then most or all of
    # the transformations that we might need could operate only on
    # the offset and frame rate. This would help maintain precision
    # since date/time data structures are often not as precise as
    # times in double precision seconds. Python's datetime class,
    # for example, keeps time only to the nearest microsecond.
    
    # Compute time of features from times of spectra.
    times = spectrogram.times
    n = len(spectra) * c.pooling_block_size[0]
    time = (times[0] + times[n - 1]) / 2.
    
    features = _normalize(spectra.flatten())
    
    # For a training set of about 9000 MPG Ranch call and noise segments
    # (roughly half call segments and half noise segments), including the
    # segment spectrogram norm did not yield a classifier that was as
    # good as the one gotten when we did not include the norm. However,
    # learning curves suggested that the classifier that included the
    # norm might be superior if trained on a larger number of examples.
    # The learning curve for features that did not include the norm rose
    # more quickly than the learning curve for features that did include
    # the norm, but also leveled off more, so that it looked like the
    # latter might eventually overtake the former.
    if c.include_norm_in_features:
        norm = np.linalg.norm(spectra)
        features = np.hstack([features, norm])
    
    return (features, spectra, time)


def _freq_to_index(freq, sample_rate, dft_size):
    bin_size = sample_rate / dft_size
    return int(round(freq / bin_size))


def _sum_adjacent(x, dims):
    
    m, n = dims
    xm, xn = x.shape
    
    xm = (xm // m) * m
    xn = (xn // n) * n
    x = x[:xm, :xn]
    
    # Sum columns.
    x.shape = (xm, xn / n, n)
    x = x.sum(2)
    xn /= n
    
    # Sum rows.
    x = x.transpose()
    x.shape = (xn, xm / m, m)
    x = x.sum(2)
    x = x.transpose()
    
    return x
    
    
def _test_sum_adjacent():
    x = np.arange(24)
    x.shape = (4, 6)
    print(x)
    x = _sum_adjacent(x, 2, 3)
    print(x)


def _normalize(x):
    norm = np.linalg.norm(x)
    return x / norm if norm != 0 else x

