"""Utility functions for time-frequency analysis."""


import numpy as np


'''
TODO: Reconsider time frequency analysis terminology. I think it
might be good, for example, to use the term "record" (or maybe something
else, e.g. "vector", though "record" is my favorite at the moment) to
refer to a vector of samples that is analyzed, say by applying a window
and then computing a DFT. The first step of the analyses we intend to
support is always to generate a sequence of uniformly-sized sample
vectors from a continuous sample sequence, with each vector to be
analyzed subsequently in the same way, and it seems like it would be
a good idea to have a name for each of the vectors.
'''


def get_dft_analysis_data(sample_rate, window_size, dft_size=None):

    if dft_size is None:
        dft_size = get_dft_size(window_size)

    freqs = get_dft_freqs(sample_rate, dft_size)

    return (dft_size, freqs)


def get_dft_size(window_size):

    """
    Returns the smallest power of two that is at least the specified
    window size.
    """

    dft_size = 1
    while dft_size < window_size:
        dft_size <<= 1

    return dft_size


def get_dft_freqs(sample_rate, dft_size):

    """
    Gets the frequencies of a DFT analysis.

    It is assumed that the analyzed signal is real, so that the
    analysis will be performed at `dft_size // 2 + 1` frequencies.
    """

    num_freqs = dft_size // 2 + 1
    spacing = sample_rate / dft_size
    return np.arange(num_freqs) * spacing


def get_dft_bin_num(freq, sample_rate, dft_size):
    
    """
    Gets the DFT bin number for a specified frequency.
    
    The bin number is in [0, `dft_size`).
    """
    
    bin_size = sample_rate / dft_size
    
    # Modulo operation puts any frequency into the appropriate bin
    # with number in [0, dft_size).
    return int(round(freq / bin_size)) % dft_size


def get_num_analysis_records(num_samples, record_size, hop_size):

    if record_size <= 0:
        raise ValueError('Record size must be positive.')

    elif hop_size <= 0:
        raise ValueError('Hop size must be positive.')

    elif hop_size > record_size:
        raise ValueError('Hop size must not exceed record size.')

    if num_samples < record_size:
        # not enough samples for any records

        return 0

    else:
        # have enough samples for at least one record

        overlap = record_size - hop_size
        return (num_samples - overlap) // hop_size


def compute_spectrogram(samples, window, hop_size, dft_size=None):

    """
    Computes the spectrogram of a real signal.

    The spectrogram is the squared magnitude of the short-time
    Fourier transform.
    """

    stft = compute_stft(samples, window, hop_size, dft_size)
    magnitudes = np.abs(stft)
    return magnitudes * magnitudes


def compute_stft(samples, window, hop_size, dft_size=None):

    """Computes the short-time Fourier transform (STFT) of a real signal."""

    window_size = len(window)

    if dft_size is None:
        dft_size = get_dft_size(window_size)

    records = _get_analysis_records(samples, len(window), hop_size)
    windowed_records = window * records
    stft = np.fft.rfft(windowed_records, n=dft_size)
    return stft


def _get_analysis_records(samples, record_size, hop_size):

    """
    Creates a sequence of hopped sample records from the specified samples.

    This method uses a NumPy array stride trick to create the desired
    sequence as a view of the input samples that can be created at very
    little cost. The caveat is that the view should only be read from,
    and never written to, since when the hop size is less than the
    record size the view's records overlap in memory.

    The trick is from the `_fft_helper` function of the
    `scipy.signal.spectral` module of SciPy.
    """

    # Get result shape.
    num_samples = samples.shape[-1]
    num_vectors = get_num_analysis_records(num_samples, record_size, hop_size)
    shape = samples.shape[:-1] + (num_vectors, record_size)

    # Get result strides.
    stride = samples.strides[-1]
    strides = samples.strides[:-1] + (hop_size * stride, stride)

    return np.lib.stride_tricks.as_strided(samples, shape, strides)


def scale_spectrogram(spectra, out=None):

    """
    Scale spectrogram to satisfy Parseval's Theorem.

    This function scales a spectrogram so that if it was computed with
    a rectangular window it satisfies Parseval's Theorem: the sum of
    the the bins of each spectrum of the spectrogram equals the sum of
    the squares of the samples from which it was computed.
    """

    out = _get_output_array(spectra, out)

    # We want to scale bins zero and `dft_size // 2` by `1 / dft_size`,
    # and all of the other bins by twice that amount. (The additional
    # factor of two for the other bins accounts for the energy of the
    # negative frequency bins. Bins zero and `dft_size // 2`, whose
    # center frequencies are zero and half the sample rate, have no
    # corresponding negative frequency bins.) For efficiency, we
    # perform these scalings first by scaling all bins by `2 / dft_size`
    # and then by scaling the first and last bins by one half.

    num_bins = out.shape[-1]
    if num_bins == 1:
        dft_size = 1
    else:
        dft_size = 2 * (num_bins - 1)

    if dft_size != 1:

        # Scale all bins by `2 / dft_size`
        if dft_size != 2:
            out *= 2 / dft_size

        # Scale first and last bins by an additional factor of one half.
        out[..., 0] *= .5
        out[..., -1] *= .5

    return out


def _get_output_array(x, out):

    if out is None:
        out = np.array(x)

    elif out is not x:
        np.copyto(out, x)

    return out


# It's important not to make this too small, so that it is representable
# as a 32-bit floating point number. The smallest normal (i.e. not
# denormalized) positive floating point number is about 1.18e-38.
SMALL_POWER = 1e-30
SMALL_POWER_DB = 10 * np.log10(SMALL_POWER)


def linear_to_log(spectra, reference_power=1., out=None):

    """Converts linear spectral values to logarithmic ones."""

    out = _get_output_array(spectra, out)

    if reference_power is not None and reference_power != 1:
        out /= reference_power

    # We substitute `SMALL_POWER` for small values in the spectra
    # before taking logs to avoid divide by zero error messages
    # in the call to `np.log10`, and to avoid minus infinity
    # values in the output. Having large negative numbers is
    # preferable to having infinities since the latter do not
    # play well with other numbers in subsequent arithmetic
    # (for example 0 times infinity is `NaN`).
    out[out < SMALL_POWER] = SMALL_POWER

    np.log10(out, out=out)

    out *= 10

    return out


def log_to_linear(spectra, reference_power=1., out=None):

    """Converts logarithmic spectral values to linear ones."""

    out = _get_output_array(spectra, out)

    out /= 10

    if reference_power != 1:
        out += np.log10(reference_power)

    np.power(10, out, out=out)

    return out


# TODO: Revisit this function, and consider renaming and/or reimplementing
# it. The current implementation clips spectral values below according to
# order statistical thresholds. We use the function to reduce the variation
# within spectra that contain only background noise. This isn't what is
# usually meant by the term "denoising", however, which usually implies
# *zeroing* bins that are deemed to contain only background noise.
def denoise(spectra, percentile=50, out=None):

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
