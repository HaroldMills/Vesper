import timeit

import numpy as np


DURATION = 100
NUM_TRIALS = 5
INPUT_SAMPLE_RATE = 22050
OUTPUT_SAMPLE_RATE = 24000

SETUP = '''
import math

from scipy import signal
import resampy

gcd = math.gcd(INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE)
up = OUTPUT_SAMPLE_RATE / gcd
down = INPUT_SAMPLE_RATE / gcd

n = int(round(DURATION * INPUT_SAMPLE_RATE))
x = np.random.randn(n)
'''

# STATEMENT = '''
# y = resampy.resample(x, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE)
# '''

STATEMENT = '''
y = signal.resample_poly(x, up, down)
'''


def main():

    print(
        ('Resampling {} seconds of audio from {} hertz to {} hertz '
         '{} times...').format(
             DURATION, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, NUM_TRIALS))
    
    times = timeit.repeat(
        stmt=STATEMENT, setup=SETUP, repeat=NUM_TRIALS, number=1,
        globals=globals())
    
    times = np.array(times)
    rates = DURATION / times
    print('Rates for all trials:', rates)
    
    time = min(times)
    rate = DURATION / time
    print(
        ('Fastest trial resampled {} seconds of audio in {:.1f} '
         'seconds, {:.1f} times faster than real time.').format(
             DURATION, time, rate))


if __name__ == '__main__':
    main()
