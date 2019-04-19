"""
Compares spectrogram computations with TensorFlow and Vesper.

As of 2018-11-09, Vesper is a little more than three times faster than
TensorFlow at computing spectrograms with a DFT size of 128.
"""


import functools
import time

import numpy as np
import tensorflow as tf

import vesper.util.data_windows as data_windows
import vesper.util.time_frequency_analysis_utils as tfa_utils


SHOW_SPECTROGRAMS = False

SAMPLE_RATE = 24000   # Hertz
AMPLITUDE = 1
FREQUENCY = 3000      # Hertz
DURATION = 1000       # seconds

WINDOW_SIZE = .005    # seconds
HOP_SIZE = .5         # fraction of window size

if SHOW_SPECTROGRAMS:
    SAMPLE_RATE = 1
    FREQUENCY = .25
    DURATION = 8
    WINDOW_SIZE = 8
    HOP_SIZE = 1


def main():
    
    waveform = create_waveform()
    
    window_size = int(round(WINDOW_SIZE * SAMPLE_RATE))
    print('Window size is {} samples.'.format(window_size))
    
    hop_size = int(round(window_size * HOP_SIZE))
    print('Hop size is {} samples.'.format(hop_size))
    
    gram = compute_tensorflow_spectrogram(waveform, window_size, hop_size)
    if SHOW_SPECTROGRAMS:
        print(gram)
        
    gram = compute_vesper_spectrogram(waveform, window_size, hop_size)
    if SHOW_SPECTROGRAMS:
        print(gram)
    
    
def create_waveform():
    length = int(round(DURATION * SAMPLE_RATE))
    print('Waveform length is {} samples.'.format(length))
    phases = 2 * np.pi * FREQUENCY / SAMPLE_RATE * np.arange(length)
    return AMPLITUDE * np.cos(phases)


def compute_tensorflow_spectrogram(waveform, window_size, hop_size):
    
    waveform_ = tf.placeholder(tf.float32)
    window_fn = functools.partial(tf.signal.hann_window, periodic=True)
    stft = tf.signal.stft(
        waveform_, window_size, hop_size, window_fn=window_fn)
    gram = tf.real(stft * tf.conj(stft))
    
    with tf.Session() as sess:
        
        print('Computing TensorFlow spectrogram...')
        start_time = time.time()
        g = sess.run(gram, feed_dict={waveform_: waveform})
        end_time = time.time()
        print('Done.')
        
    report_performance(g, start_time, end_time)
        
    return g


def report_performance(gram, start_time, end_time):
    
    num_spectra = len(gram)
    delta = end_time - start_time
    
    print('Computed {} spectra in {:.1f} seconds.'.format(num_spectra, delta))
    
    micros = int(round(1000000 * delta / num_spectra))
    speedup = DURATION / delta
    
    print((
        "That's {} microseconds per spectrum, or {} times faster than "
        "real time.").format(micros, speedup))
    

def compute_vesper_spectrogram(waveform, window_size, hop_size):

    window = data_windows.create_window('Hann', window_size).samples
    
    print('Computing Vesper spectrogram...')
    start_time = time.time()
    gram = tfa_utils.compute_spectrogram(waveform, window, hop_size)
    end_time = time.time()
    print('Done.')
    
    report_performance(gram, start_time, end_time)
    
    return gram


if __name__ == '__main__':
    main()
