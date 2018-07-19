"""Signal generation utility functions."""


import numpy as np

import vesper.util.signal_utils as signal_utils


def add_tone(
        sound, start_time, duration, amplitude, frequency,
        channel_num=0, taper_duration=0):
    
    fs = sound.sample_rate
    
    # Create tone.
    length = signal_utils.seconds_to_frames(duration, fs)
    phases = np.arange(length) * 2 * np.pi * frequency / fs
    tone = amplitude * np.sin(phases)
    
    # Taper ends if specified.
    if taper_duration != 0:
        n = signal_utils.seconds_to_frames(taper_duration, fs)
        ramp = np.arange(n) / n
        tone[:n] *= ramp
        tone[-n:] *= 1 - ramp
    
    # Add tone to sound.
    start_index = signal_utils.seconds_to_frames(start_time, fs)
    sound.samples[channel_num, start_index:start_index + length] += tone
