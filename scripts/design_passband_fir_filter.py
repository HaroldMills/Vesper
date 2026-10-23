"""
Design an FIR filter with `scipy.signal.remez` and plot its frequency response.
"""


import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import freqz, remez


# Filter design parameters.
SAMPLE_RATE = 22050        # Hz
FILTER_LENGTH = 89         # taps
CUTOFF = 6000              # Hz
PASSBAND = (6000, 10000)   # Hz
TRANSITION_WIDTH = 500     # Hz


def design_highpass_filter():

    nyquist = SAMPLE_RATE / 2

    stopband_edge = CUTOFF - TRANSITION_WIDTH

    bands = [
        0, stopband_edge,
        CUTOFF, nyquist]
    desired = [0, 1]
    weight = [10, 1]

    return remez(FILTER_LENGTH, bands, desired, weight=weight, fs=SAMPLE_RATE)


def design_bandpass_filter():

    nyquist = SAMPLE_RATE / 2

    lower_stopband_edge = PASSBAND[0] - TRANSITION_WIDTH
    upper_stopband_edge = PASSBAND[1] + TRANSITION_WIDTH

    bands = [
        0, lower_stopband_edge,
        PASSBAND[0], PASSBAND[1],
        upper_stopband_edge, nyquist]
    desired = [0, 1, 0]
    weight = [10, 1, 10]

    return remez(FILTER_LENGTH, bands, desired, weight=weight, fs=SAMPLE_RATE)


def plot_frequency_response(coefficients):

    freqs, response = freqz(coefficients, worN=8192, fs=SAMPLE_RATE)
    magnitude_db = 20 * np.log10(np.maximum(np.abs(response), 1e-10))

    _, axes = plt.subplots(figsize=(10, 6))

    axes.plot(freqs, magnitude_db)
    axes.set_xlim(0, SAMPLE_RATE / 2)
    axes.set_ylim(-80, 5)
    axes.set_xlabel('Frequency (Hz)')
    axes.set_ylabel('Magnitude (dB)')
    axes.set_title(
        f'Frequency Response Magnitude '
        f'(filter length {FILTER_LENGTH})')
    axes.grid(True)

    # for edge in (
    #         PASSBAND[0] - TRANSITION_WIDTH, PASSBAND[0],
    #         PASSBAND[1], PASSBAND[1] + TRANSITION_WIDTH):
    #     axes.axvline(edge, color='gray', linestyle='--', linewidth=0.8)

    plt.tight_layout()
    plt.show()


def main():
    coefficients = design_highpass_filter()
    plot_frequency_response(coefficients)


if __name__ == '__main__':
    main()
