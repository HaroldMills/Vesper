"""Times the computation of a spectrogram of an audio file."""


from pathlib import Path
import time

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


DIR_PATH = Path('/Volumes/Recordings1/Nocturnal Bird Migration/Harold/2020')
FILE_PATH = DIR_PATH / 'Harold_2020-04-02_00.32.33_Z.wav'

WINDOW_SIZE = .005
HOP_SIZE = .0025

APPROXIMATE_READ_SIZE = 100000


def main():
    
    start_time = time.time()
    
    reader = WaveAudioFileReader(str(FILE_PATH), mono_1d=True)
    sample_rate = reader.sample_rate

    window_size = int(round(WINDOW_SIZE * sample_rate))
    hop_size = int(round(HOP_SIZE * sample_rate))
    dft_size = tfa_utils.get_dft_size(window_size)
    
    print('window size', window_size)
    print('hop size', hop_size)
    print('DFT size', dft_size)
    
    spectrum_count = int(round(APPROXIMATE_READ_SIZE / hop_size))
    usual_read_size = (spectrum_count - 1) * hop_size + window_size
    window = HannWindow(window_size).samples
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
    duration = length / sample_rate
    rate = duration / elapsed
    print(
        f'Processed {duration:.1f} seconds of audio in {elapsed:.1f} '
        f'seconds, {rate:.1f} times faster than real time.')


if __name__ == '__main__':
    main()
