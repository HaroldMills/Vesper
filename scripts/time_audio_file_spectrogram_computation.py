"""Times the computation of a spectrogram of an audio file."""


from pathlib import Path
import time


from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Harold/2018 Harold Archive/Recordings')
FILE_PATH = DIR_PATH / 'Harold_2018-06-01_00.05.45_Z.wav'

APPROXIMATE_READ_SIZE = 100000

WINDOW_SIZE = 100
HOP_SIZE = 50
DFT_SIZE = 128


def main():
    
    start_time = time.time()
    
    num_spectra = int(round(APPROXIMATE_READ_SIZE / HOP_SIZE))
    usual_read_size = (num_spectra - 1) * HOP_SIZE + WINDOW_SIZE
    window = HannWindow(WINDOW_SIZE).samples
    reader = WaveAudioFileReader(str(FILE_PATH), mono_1d=True)
    length = reader.length
    index = 0
    while length - index >= WINDOW_SIZE:
        # print(index)
        read_size = min(usual_read_size, length - index)
        samples = reader.read(index, read_size)
        gram = tfa_utils.compute_spectrogram(
            samples, window, HOP_SIZE, DFT_SIZE)
        num_spectra = gram.shape[0]
        index += num_spectra * HOP_SIZE
        
    end_time = time.time()
    elapsed = end_time - start_time
    duration = reader.length / reader.sample_rate
    rate = duration / elapsed
    print(
        ('Processed {:.1f} seconds of audio in {:.1f} seconds, {:.1f} '
         'times faster than real time.').format(duration, elapsed, rate))
    
    
if __name__ == '__main__':
    main()
