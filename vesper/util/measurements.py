"""
Clip spectrum measurements.

The code in this module was used by NFC coarse and species classifiers
that I developed for MPG Ranch in 2016. I deleted those classifiers,
which were in modules `vesper.util.nfc_coarse_classifier` and
`vesper.util.nfc_species_classifier`, on 2022-06-21 since the coarse
classifier has been superseded by a better one and the species
classifier did not work well enough to be useful. I retained this
module, even though it is unused, since I thought some of the code
might prove useful later and I wanted to make it relatively easy to
find.

As part of the deletion, I also moved the `_denoise` function from
`vesper.util.time_frequency_analysis_utils` to this module since it
is used only by this module.
"""


import numpy as np


def equivalent_bandwidth(x):
    return np.sum(x) / np.max(x)


_SMALL_PROBABILITY = 1e-20


def entropy(x):
    p = x / np.sum(x)
    p[p == 0] = _SMALL_PROBABILITY
    return -np.sum(p * np.log(p))


def apply_measurement_to_spectra(
        measurement, spectrogram, start_freq=None, end_freq=None,
        denoise=False, block_size=1):
    
    """Applies a measurement to each spectrum of a spectrogram."""
    
    num_spectra = len(spectrogram.spectra)
    
    if num_spectra == 0:
        return np.array([])
    
    if start_freq is None:
        start_index = 0
    else:
        start_index = int(round(start_freq / spectrogram.freq_spacing))
        
    if end_freq is None:
        end_index = len(spectrogram.spectra[0])
    else:
        end_index = int(round(end_freq / spectrogram.freq_spacing)) + 1
        
    s = spectrogram.spectra[:, start_index:end_index]
#    s = spectrogram_utils.log_to_linear(s)
    s = np.power(10, s / 10.)
    
    if denoise:
        _denoise(s, out=s)
    
    num_blocks = num_spectra - block_size + 1
    measurements = np.array([_measure(measurement, s, i, block_size)
                            for i in range(num_blocks)])
    
    t = spectrogram.times
    times = np.array([np.mean(t[i:i + block_size])
                      for i in range(num_blocks)])
    
    return measurements, times


def _measure(measurement, s, i, block_size):
    block = s[i:i + block_size]
    return measurement(block.ravel())




# TODO: Revisit this function, and consider renaming and/or reimplementing
# it. The current implementation clips spectral values below according to
# order statistical thresholds. We use the function to reduce the variation
# within spectra that contain only background noise. This isn't what is
# usually meant by the term "denoising", however, which usually implies
# *zeroing* bins that are deemed to contain only background noise.
def _denoise(spectra, percentile=50, out=None):

    """Denoises a sequence of spectra."""

    if out is None:
        out = np.array(spectra)

    elif out is not spectra:
        np.copyto(out, spectra)

    # Compute percentile spectral values across time for each frequency bin.
    percentiles = np.percentile(out, percentile, axis=0)

    # The `np.percentile` function yields an array whose dtype is float64,
    # even though `out` has dtype float32. We create an array with dtype
    # float32 to avoid implicit casting errors in subsequent arithmetic.
    percentiles = np.array(percentiles, dtype='float32')

    # Subtract percentiles from spectral values.
    out -= percentiles

    # Zero negative spectral values.
    out[out < 0.] = 0.

    # Add percentiles back.
    out += percentiles

    return out
