from multiprocessing import Pool
from pathlib import Path
import sys
import time

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


# RESUME:
#     * Implement other aggregators.
#     * Visual cue to variability?
#     * Compute grams for a whole season.
#     * Use signal package to compute spectrograms.
#     * Support multichannel recordings.


DIR_PATH = Path('/Volumes/Recordings1/Nocturnal Bird Migration/Harold/2020')
# DIR_PATH = Path('/Users/harold/Desktop')
INPUT_FILE_PATH = DIR_PATH / 'Harold_2020-04-02_00.32.33_Z.wav'
OUTPUT_FILE_PATH = Path('/Users/harold/Desktop/gram.pdf')

WINDOW_SIZE = .040                  # seconds
HOP_SIZE = .020                     # seconds
AGGREGATION_RECORD_SIZE = 60        # seconds

APPROXIMATE_CHUNK_SIZE = 20000      # sample frames

WORKER_POOL_SIZE = 4                # processes
TASK_SIZE = 50                      # spectra


def main():

    start_time = time.time()

    gram, time_step, freq_step = compute_aggregate_gram(INPUT_FILE_PATH)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f'Elapsed time was {elapsed} seconds.')

    plot_aggregate_gram(
        gram, time_step, freq_step, INPUT_FILE_PATH.name, OUTPUT_FILE_PATH)

    # print(f'Gram shape is {gram.shape}.')


def compute_aggregate_gram(file_path):

    with Pool(WORKER_POOL_SIZE) as pool:
        tasks, freq_step = get_tasks(file_path, TASK_SIZE)
        spectra = pool.starmap(compute_aggregate_spectra, tasks)
        gram = np.concatenate(spectra)
        return gram, AGGREGATION_RECORD_SIZE, freq_step


def get_tasks(file_path, task_size):

    # Get file frame count and sample rate.
    reader = WaveAudioFileReader(str(file_path))
    frame_count = reader.length
    sample_rate = reader.sample_rate
    reader.close()

    # Get size of record from which each aggregate spectrum will be
    # computed, in sample frames.
    record_size = int(round(AGGREGATION_RECORD_SIZE * sample_rate))

    # Get spectrogram settings.
    window_size = int(round(WINDOW_SIZE * sample_rate))
    hop_size = int(round(HOP_SIZE * sample_rate))
    dft_size = tfa_utils.get_dft_size(window_size)

    # Get number of spectra in aggregate gram.
    gram_size = int(frame_count // record_size)

    # Get tasks, each of which will compute up to `task_size` spectra.
    tasks = []
    start_spectrum_num = 0
    while start_spectrum_num != gram_size:
        spectrum_count = min(task_size, gram_size - start_spectrum_num)
        tasks.append((
            file_path, start_spectrum_num, spectrum_count, record_size,
            window_size, hop_size, dft_size))
        start_spectrum_num += spectrum_count

    freq_step = sample_rate / dft_size

    return tasks, freq_step


# TODO: Handle multichannel files.
def compute_aggregate_spectra(
        file_path, start_spectrum_num, spectrum_count, record_size,
        window_size, hop_size, dft_size):

    print(f'{file_path.name} {start_spectrum_num} {spectrum_count}')

    reader = WaveAudioFileReader(str(file_path))
    window = HannWindow(window_size).samples

    spectrum_size = int(dft_size / 2) + 1
    spectra = np.zeros((spectrum_count, spectrum_size))

    start_sample_num = start_spectrum_num * record_size

    for i in range(spectrum_count):

        samples = reader.read(start_sample_num, record_size)[0, :]

        gram = compute_spectrogram(samples, window, hop_size, dft_size)

        spectra[i, :] = np.average(gram, 0)

        start_sample_num += record_size

    reader.close()

    tfa_utils.scale_spectrogram(spectra, out=spectra)

    tfa_utils.linear_to_log(spectra, out=spectra)

    return spectra


def compute_spectrogram(samples, window, hop_size, dft_size):

    sample_count = len(samples)
    window_size = len(window)

    # Allocate storage for gram.
    spectrum_count = get_spectrum_count(sample_count, window_size, hop_size)
    spectrum_size = int(dft_size / 2) + 1
    gram = np.zeros((spectrum_count, spectrum_size))
    
    gram_chunk_size = \
        get_spectrum_count(APPROXIMATE_CHUNK_SIZE, window_size, hop_size)
    waveform_chunk_size = (gram_chunk_size - 1) * hop_size + window_size
    waveform_increment = gram_chunk_size * hop_size
    
    start_sample_num = 0
    start_spectrum_num = 0

    while start_spectrum_num != spectrum_count:

        # print(start_spectrum_num, spectrum_count)

        read_size = min(waveform_chunk_size, sample_count - start_sample_num)
        end_sample_num = start_sample_num + read_size
        waveform_chunk = samples[start_sample_num:end_sample_num]

        gram_chunk = tfa_utils.compute_spectrogram(
            waveform_chunk, window, hop_size, dft_size)

        end_spectrum_num = start_spectrum_num + gram_chunk.shape[0]
        gram[start_spectrum_num:end_spectrum_num] = gram_chunk

        start_sample_num += waveform_increment
        start_spectrum_num = end_spectrum_num

    return gram


def get_spectrum_count(sample_count, window_size, hop_size):
    return int((sample_count - window_size) // hop_size) + 1


def plot_aggregate_gram(gram, time_step, freq_step, title, file_path):

    with PdfPages(file_path) as pdf:
        
        plt.figure(figsize=(6, 3))
        
        start_time = 0
        end_time = gram.shape[0] * time_step / 3600
        start_freq = 0
        end_freq = (gram.shape[1] - 1) * freq_step
        extent = (start_time, end_time, start_freq, end_freq)
        
        # `vmin` and `vmax` were chosen by looking at histogram of spectrogram
        # values plotted by `plot_histogram` function.
        #
        # A few colormaps: gray_r, viridis, plasma, inferno, magma, cividis
        plt.imshow(
            gram.T, cmap='gray_r', vmin=0, vmax=100, origin='lower',
            extent=extent, aspect='auto')
        
        plt.title(title)
        plt.xlabel('Time (hours)')
        plt.ylabel('Frequency (Hz)')
        # plt.ylim(0, 11000)

        pdf.savefig()
        
        plt.close()


if __name__ == '__main__':
    main()
