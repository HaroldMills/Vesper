"""Times the computation of a spectrogram of an audio file."""


from pathlib import Path
import time

import numpy as np

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


DIR_PATH = Path('/Volumes/Recordings1/Nocturnal Bird Migration/Harold/2020')
FILE_PATH = DIR_PATH / 'Harold_2020-04-02_00.32.33_Z.wav'

WINDOW_SIZE = .005               # seconds
HOP_SIZE = .0025                 # seconds, must divide `AGGREGATION_DURATION`
AGGREGATION_DURATION = 60        # seconds

APPROXIMATE_READ_SIZE = 100000


def main():
    
    start_time = time.time()
    
    reader = WaveAudioFileReader(str(FILE_PATH), mono_1d=True)
    sample_rate = reader.sample_rate

    spectrograph = create_spectrograph(WINDOW_SIZE, HOP_SIZE, sample_rate)

    print('window size', spectrograph.window_size)
    print('hop size', spectrograph.hop_size)
    print('DFT size', spectrograph.dft_size)
    
    usual_read_size = get_usual_read_size(APPROXIMATE_READ_SIZE, spectrograph)
    length = reader.length
    waveform_index = 0
    while length - waveform_index >= spectrograph.window_size:
        read_size = min(usual_read_size, length - waveform_index)
        samples = reader.read(waveform_index, read_size)
        gram = spectrograph.process(samples)
        spectrum_count = len(gram)
        waveform_index += spectrum_count * spectrograph.hop_size
        
    end_time = time.time()
    elapsed = end_time - start_time
    duration = length / sample_rate
    rate = duration / elapsed
    print(
        f'Processed {duration:.1f} seconds of audio in {elapsed:.1f} '
        f'seconds, {rate:.1f} times faster than real time.')


def create_spectrograph(window_size, hop_size, sample_rate):
    window_size = int(round(WINDOW_SIZE * sample_rate))
    hop_size = int(round(HOP_SIZE * sample_rate))
    return Spectrograph(window_size, hop_size)


def get_usual_read_size(approximate_read_size, spectrograph):
    window_size = spectrograph.window_size
    hop_size = spectrograph.hop_size
    spectrum_count = int(round(approximate_read_size / hop_size))
    return (spectrum_count - 1) * hop_size + window_size


class Spectrograph:

    def __init__(self, window_size, hop_size):

        self.window_size = window_size
        self.hop_size = hop_size

        self._window = HannWindow(window_size).samples
        self.dft_size = tfa_utils.get_dft_size(self.window_size)


    def process(self, samples):
        return tfa_utils.compute_spectrogram(
            samples, self._window, self.hop_size, self.dft_size)


if __name__ == '__main__':
    main()
