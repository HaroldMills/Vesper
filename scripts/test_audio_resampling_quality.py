"""Plots spectrograms of a chirp resampled by various methods."""


from pathlib import Path
import math

from matplotlib.backends.backend_pdf import PdfPages
from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import resampy

import vesper.signal.resampling_utils as resampling_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


PDF_DIR_PATH = Path('/Users/harold/Desktop/Audio Resampling Tests')


def main():
    test_resampling(22000, 24000)
    test_resampling(32000, 24000)
    test_resampling(44000, 24000)
    test_resampling(48000, 24000)
    
    
def test_resampling(input_rate, output_rate):
    
    file_name = \
        'Resample from {} Hz to {} Hz.pdf'.format(input_rate, output_rate)
    file_path = PDF_DIR_PATH / file_name
    
    with PdfPages(file_path) as pdf_file:
        
        samples = create_test_signal(input_rate)
        
        show_stats('original', samples)
        
        plot_spectrogram(samples, input_rate, 'Test Input', pdf_file)
        
        test_resampling_utils(samples, input_rate, output_rate, pdf_file)
        
        for N in (10, 100, 1000):
            test_resample_poly(samples, input_rate, output_rate, N, pdf_file)
             
        for filter_name in ('kaiser_best', 'kaiser_fast'):
            test_resampy(
                samples, input_rate, output_rate, filter_name, pdf_file)
    
    
def create_test_signal(sample_rate):
    
    amplitude = 15000
    duration = 5
    taper_duration = .05
    
    # Create sine.
    freq = 8000
    sine = create_sine(
        sample_rate, np.float64, amplitude, freq, duration, taper_duration)
    
    # Create chirp.
    start_freq = 0
    end_freq = sample_rate / 2
    chirp = create_chirp(
        sample_rate, np.float64, amplitude, start_freq, end_freq, duration,
        taper_duration)
    
    # Sum.
    samples = sine + chirp
    
    # Scale to desired overall amplitude.
    overall_amplitude = 30000
    samples *= overall_amplitude / np.max(np.abs(samples))
    
    # Quantize to 16 bits.
    samples = np.round(samples).astype('int16')
    
    return samples
    
    
    
def create_sine(
        sample_rate, sample_dtype, amplitude, freq, duration, taper_duration):
    
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    phases = 2 * np.pi * freq * times
    sine = amplitude * np.sin(phases)
    
    taper_ends(sine, sample_rate, taper_duration)
    
    return sine.astype(sample_dtype)
    
    
def taper_ends(samples, sample_rate, taper_duration):
    
    # Taper ends.
    taper_length = int(round(taper_duration * sample_rate))
    taper = np.arange(taper_length) / float(taper_length)
    samples[:taper_length] *= taper
    samples[-taper_length:] *= 1 - taper
    
    return samples


def create_chirp(
        sample_rate, sample_dtype, amplitude, start_freq, end_freq, duration,
        taper_duration):
    
    # Compute chirp.
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    delta_freq = end_freq - start_freq
    freqs = start_freq + delta_freq * times / (2 * duration)
    phases = 2. * np.pi * freqs * times
    chirp = amplitude * np.sin(phases)
    
    taper_ends(chirp, sample_rate, taper_duration)
    
    return chirp.astype(sample_dtype)
    
    
def show_stats(name, samples):
    
    n = len(samples)
    
    # Use double precision to compute mean squared sample to avoid overflow.
    x = samples.astype('float64')
    mean_squared = np.sqrt(np.sum(x * x) / n)
    
    print('{}: {} {} {} {} {}'.format(
        name, n, samples.dtype, np.max(samples), np.min(samples),
        mean_squared))
    
    
def plot_spectrogram(samples, sample_rate, title, pdf_file):
    
    window_size_sec = .005
    hop_size_percent = 20
    
    window_size = int(round(window_size_sec * sample_rate))
    window = signal.hanning(window_size, sym=False)
    hop_size = \
        int(round(window_size_sec * hop_size_percent / 100 * sample_rate))
        
    dft_size = 2 * tfa_utils.get_dft_size(window_size)
    
    gram = tfa_utils.compute_spectrogram(samples, window, hop_size, dft_size)
    
    gram = tfa_utils.linear_to_log(gram)
    
    # plot_histogram(gram)
    
    hop_size_sec = window_size_sec * hop_size_percent / 100
    times = np.arange(len(gram)) * hop_size_sec + window_size_sec / 2
    
    num_bins = dft_size / 2 + 1
    bin_size = sample_rate / dft_size
    freqs = np.arange(num_bins) * bin_size
        
    x = gram.transpose()
    
    plt.figure(figsize=(12, 6))
        
    start_time = times[0] - hop_size_sec / 2
    end_time = times[-1] + hop_size_sec / 2
    start_freq = freqs[0]
    end_freq = freqs[-1]
    extent = (start_time, end_time, start_freq, end_freq)
    
    # `vmin` and `vmax` were chosen by looking at histogram of spectrogram
    # values plotted by `plot_histogram` function.
    plt.imshow(
        x, cmap='gray_r', vmin=-25, vmax=125, origin='lower', extent=extent,
        aspect='auto')
    
    plt.title(title)
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    # plt.ylim(0, 11000)

    pdf_file.savefig()
    
    plt.close()


def plot_histogram(x):
    
    num_bins = 300
    min_value = -100
    max_value = 200
    
    histogram, edges = np.histogram(x, num_bins, (min_value, max_value))
    distribution = histogram / histogram.sum()
    
#     bin_size = (max_value - min_value) / num_bins
#     edges = min_value + np.arange(num_bins + 1) * bin_size
    
    plt.figure(1)
    plt.plot(edges[:-1], distribution)
    plt.xlim((edges[0], edges[-1]))
    plt.title('Distribution of Spectrogram Values')
    plt.xlabel('Log Power')
    plt.show()


def test_resampling_utils(samples, input_rate, output_rate, pdf_file):
    
    if output_rate != 24000:
        raise ValueError(
            'Sorry, but resampling_utils.resample only supports '
            'resampling to 24000 Hz.')
        
    # Resample chirp.
    samples = resampling_utils.resample_to_24000_hz(samples, input_rate)
    
    show_stats('resampling_utils', samples)
    
    # Plot spectrogram of result.
    plot_spectrogram(samples, output_rate, 'resampling_utils', pdf_file)
    
    
def test_resample_poly(samples, input_rate, output_rate, N, pdf_file):
    
    # Resample chirp.
    samples = resample_poly(samples, input_rate, output_rate, N)
    
    # Plot spectrogram of result.
    title = 'resample_poly N = {}'.format(N)
    show_stats(title, samples)
    plot_spectrogram(samples, output_rate, title, pdf_file)


def resample_poly(samples, input_rate, output_rate, N):
    
    # Ensure that `input_rate` and `output_rate` are integers, since `math.gcd`
    # rejects floats.
    input_rate = int(input_rate)
    output_rate = int(output_rate)
    
    gcd = math.gcd(input_rate, output_rate)
    up = output_rate / gcd
    down = input_rate / gcd
    
    # The following filter design code is from the `resample_poly` function
    # of `scipy.signal.signaltools`, but with the fixed factor of 10 in the
    # `half_len` calculation replaced by `N`.
    max_rate = max(up, down)
    f_c = 1. / max_rate  # cutoff of FIR filter (rel. to Nyquist)
    half_len = N * max_rate  # reasonable cutoff for our sinc-like function
    h = signal.firwin(2 * half_len + 1, f_c, window=('kaiser', 5.0))
    
    return signal.resample_poly(samples, up, down, window=h)
    
    
def test_resampy(samples, input_rate, output_rate, filter_name, pdf_file):
    
    # Resample chirp.
    samples = resampy.resample(
        samples, input_rate, output_rate, filter=filter_name)
    
    # Plot spectrogram of result.
    title = 'Resampy {}'.format(filter_name)
    show_stats(title, samples)
    plot_spectrogram(samples, output_rate, title, pdf_file)


if __name__ == '__main__':
    main()
