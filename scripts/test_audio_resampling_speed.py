"""Times several methods of audio resampling."""


import math
import time

from scipy import signal
import numpy as np
import resampy

import vesper.signal.resampling_utils as resampling_utils


DURATION = 100
NUM_TRIALS = 5


def main():
    time_resampling(22000, 24000)
    time_resampling(32000, 24000)
    time_resampling(44000, 24000)
    time_resampling(48000, 24000)
    
    
def time_resampling(input_rate, output_rate):
    
    samples = create_test_signal(input_rate)
    
    time_resampling_utils(samples, input_rate, output_rate)
    
    for N in (10, 100, 1000):
        time_resample_poly(samples, input_rate, output_rate, N)
        
    for filter_name in ('kaiser_best', 'kaiser_fast'):
        time_resampy(samples, input_rate, output_rate, filter_name)
    
    
def create_test_signal(sample_rate):
    n = int(round(DURATION * sample_rate))
    return np.random.randn(n)
    
    
def time_resampling_utils(samples, input_rate, output_rate):
    
    def resample(samples, input_rate, output_rate):
        
        if output_rate != 24000:
            raise ValueError(
                'Sorry, but resampling_utils.resample only supports '
                'resampling to 24000 Hz.')
        
        resampling_utils.resample_to_24000_hz(samples, input_rate)
        
    time_(samples, input_rate, output_rate, resample, 'resampling_utils')
    
    
def time_(samples, input_rate, output_rate, resample, name):
    
    elapsed_times = np.zeros(NUM_TRIALS)
    
    for i in range(NUM_TRIALS):
        start_time = time.time()
        resample(samples, input_rate, output_rate)
        elapsed_times[i] = time.time() - start_time
        
    # rates = DURATION / elapsed_times
    # print('Rates for all trials:', rates)

    min_elapsed_time = np.min(elapsed_times)
    rate = DURATION / min_elapsed_time
    # print(
    #     ('Fastest trial resampled {} seconds of audio in {:.1f} '
    #      'seconds, {:.1f} times faster than real time.').format(
    #          DURATION, min_elapsed_time, rate))
    
    print('{},{},{},{:.1f}'.format(name, input_rate, output_rate, rate))

    
def time_resample_poly(samples, input_rate, output_rate, N):
    
    def resample(samples, input_rate, output_rate):
        resample_poly(samples, input_rate, output_rate, N)
        
    name = 'resample_poly ' + str(N)
    time_(samples, input_rate, output_rate, resample, name)
        
        
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
    
    
def time_resampy(samples, input_rate, output_rate, filter_name):
    
    def resample(samples, input_rate, output_rate):
        return resampy.resample(
            samples, input_rate, output_rate, filter=filter_name)
        
    name = 'resampy ' + filter_name
    time_(samples, input_rate, output_rate, resample, name)
    
    
if __name__ == '__main__':
    main()
