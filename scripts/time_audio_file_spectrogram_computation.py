"""Times the computation of a spectrogram of an audio file."""


from pathlib import Path
import time


from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


DIR_PATH = Path('/Volumes/Recordings2/Nocturnal Bird Migration/Harold/2020')
FILE_PATH = DIR_PATH / 'Harold_2020-04-02_00.32.33_Z.wav'

APPROXIMATE_READ_SIZE = 100000

SAMPLE_RATE = 24000

WINDOW_SIZE = .005
HOP_SIZE = .0025

START_FREQ = 6000
END_FREQ = 10000


def main():
    
    start_time = time.time()
    
    window_size = int(round(WINDOW_SIZE * SAMPLE_RATE))
    hop_size = int(round(HOP_SIZE * SAMPLE_RATE))
    dft_size = tfa_utils.get_dft_size(window_size)
    
    print('window size', window_size)
    print('hop size', hop_size)
    print('DFT size', dft_size)
    
    num_spectra = int(round(APPROXIMATE_READ_SIZE / hop_size))
    usual_read_size = (num_spectra - 1) * hop_size + window_size
    window = HannWindow(window_size).samples
    reader = WaveAudioFileReader(str(FILE_PATH), mono_1d=True)
    length = reader.length
    index = 0
    while length - index >= window_size:
        # print(index)
        read_size = min(usual_read_size, length - index)
        samples = reader.read(index, read_size)
        gram = tfa_utils.compute_spectrogram(
            samples, window, hop_size, dft_size)
        # inband_powers = compute_inband_powers(gram)
        num_spectra = len(gram)
        index += num_spectra * hop_size
        
    end_time = time.time()
    elapsed = end_time - start_time
    duration = reader.length / reader.sample_rate
    rate = duration / elapsed
    print(
        ('Processed {:.1f} seconds of audio in {:.1f} seconds, {:.1f} '
         'times faster than real time.').format(duration, elapsed, rate))
    
    
def compute_inband_powers(gram):
    dft_size = 2 * (gram.shape[1] - 1)
    start_bin_num = get_bin_num(START_FREQ, dft_size)
    end_bin_num = get_bin_num(END_FREQ, dft_size)
    powers = gram[:, start_bin_num:end_bin_num].sum(axis=1)
    return powers


def get_bin_num(freq, dft_size):
    bin_size = SAMPLE_RATE / dft_size
    return int(round(freq / bin_size))
    
    
if __name__ == '__main__':
    main()
