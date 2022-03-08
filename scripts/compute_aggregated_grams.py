"""
Script that computes aggregated spectrograms of long recordings.

The aggregation product can be either averages or percentiles.

I wrote this script mostly to explore the relative efficiency of
various approaches to computing aggregated spectrograms. For example,
I wanted to see how the size of the waveform chunks from which
(unaveraged) spectrograms are computed influences speed, how much
the use of multiple processes can help, and how much of a difference
it makes if the waveform is on an internal disk instead of an
external one.

Things learned so far with this script:

* For results to be representative of real-world situations, it seems
  to be important to time operations on a group of long audio files,
  not on just one, at least when an external disk is involved. When I
  repeatedly timed operations on a single file on an external disk,
  reported performance was sometimes much higher than when I timed
  operations on several (e.g. seven) files. This might have to do
  with the size of some cache somewhere, either on the external disk
  or in the OS software that interacts with it.

* The size of the waveform chunks from which spectrograms are
  computed before aggregation is important. The optimal size appears
  to be fairly small, say tens of thousands of samples. I suspect
  this has to do with the size of CPU caches. The optimal size
  presumably depends on the particular computer on which the code
  is running. So it might be helpful to provide a Vesper command
  that runs some test computations to find a good chunk size.

* Using multiple processes can help, though as you would expect
  the factor by which computation is sped up decreases as the
  number of processors increases.
  
* It can help a lot to have audio files on an internal SSD instead
  of an external hard disk. The output below shows that for my
  2019 MacBook Pro and an external USB hard drive, computation
  of spectrograms for audio files on the internal SSD is about
  three times faster than for files on an external USB hard drive.


File Location,File Name,File Duration,Computation Time,Computation Rate
internal disk,Harold_2021-08-27_00.49.34_Z.wav,32760,6.1,5332
internal disk,Harold_2021-08-28_00.47.55_Z.wav,32940,6.3,5267
internal disk,Harold_2021-08-29_00.46.16_Z.wav,33060,6.9,4798
internal disk,Harold_2021-08-30_00.44.36_Z.wav,33240,6.5,5131
internal disk,Harold_2021-08-31_00.42.56_Z.wav,33420,6.8,4939
internal disk,Harold_2021-09-01_00.41.15_Z.wav,33600,6.5,5134
internal disk,Harold_2021-09-02_00.39.33_Z.wav,33720,6.7,5024
external disk,Harold_2021-08-27_00.49.34_Z.wav,32760,20.6,1591
external disk,Harold_2021-08-28_00.47.55_Z.wav,32940,21.6,1523
external disk,Harold_2021-08-29_00.46.16_Z.wav,33060,21.5,1535
external disk,Harold_2021-08-30_00.44.36_Z.wav,33240,21.8,1528
external disk,Harold_2021-08-31_00.42.56_Z.wav,33420,20.1,1665
external disk,Harold_2021-09-01_00.41.15_Z.wav,33600,20.3,1655
external disk,Harold_2021-09-02_00.39.33_Z.wav,33720,21.4,1578


In addition to testing the speed of spectrogram computations, this
script can test the speed of certain kinds of related audio file
reads: see the `time_audio_file_ops` function. Below is output from
that function comparing sequential reads with and without seeks
before each read for audio files on an internal SSD and an external
USB drive on my 2019 MacBook Pro. Reads from the internal disk are
much faster, and the difference would seem to explain most of the
differences in the spectrogram computation times listed above.


Operation,File Location,File Name,Operation Time
read without seeks,internal disk,Harold_2021-08-27_00.49.34_Z.wav,0.48
read without seeks,internal disk,Harold_2021-08-28_00.47.55_Z.wav,0.47
read without seeks,internal disk,Harold_2021-08-29_00.46.16_Z.wav,0.48
read without seeks,internal disk,Harold_2021-08-30_00.44.36_Z.wav,0.51
read without seeks,internal disk,Harold_2021-08-31_00.42.56_Z.wav,0.61
read without seeks,internal disk,Harold_2021-09-01_00.41.15_Z.wav,0.48
read without seeks,internal disk,Harold_2021-09-02_00.39.33_Z.wav,0.49
read without seeks,external disk,Harold_2021-08-27_00.49.34_Z.wav,14.90
read without seeks,external disk,Harold_2021-08-28_00.47.55_Z.wav,13.58
read without seeks,external disk,Harold_2021-08-29_00.46.16_Z.wav,13.97
read without seeks,external disk,Harold_2021-08-30_00.44.36_Z.wav,14.06
read without seeks,external disk,Harold_2021-08-31_00.42.56_Z.wav,12.62
read without seeks,external disk,Harold_2021-09-01_00.41.15_Z.wav,12.81
read without seeks,external disk,Harold_2021-09-02_00.39.33_Z.wav,13.64
read with seeks,internal disk,Harold_2021-08-27_00.49.34_Z.wav,0.71
read with seeks,internal disk,Harold_2021-08-28_00.47.55_Z.wav,0.71
read with seeks,internal disk,Harold_2021-08-29_00.46.16_Z.wav,0.82
read with seeks,internal disk,Harold_2021-08-30_00.44.36_Z.wav,0.78
read with seeks,internal disk,Harold_2021-08-31_00.42.56_Z.wav,0.73
read with seeks,internal disk,Harold_2021-09-01_00.41.15_Z.wav,0.70
read with seeks,internal disk,Harold_2021-09-02_00.39.33_Z.wav,0.70
read with seeks,external disk,Harold_2021-08-27_00.49.34_Z.wav,13.23
read with seeks,external disk,Harold_2021-08-28_00.47.55_Z.wav,13.51
read with seeks,external disk,Harold_2021-08-29_00.46.16_Z.wav,14.09
read with seeks,external disk,Harold_2021-08-30_00.44.36_Z.wav,14.05
read with seeks,external disk,Harold_2021-08-31_00.42.56_Z.wav,12.65
read with seeks,external disk,Harold_2021-09-01_00.41.15_Z.wav,12.77
read with seeks,external disk,Harold_2021-09-02_00.39.33_Z.wav,13.72


All of the above outputs (i.e. both sets) were from script runs with
the following settings:

WINDOW_SIZE = .040                  # seconds
HOP_SIZE = .020                     # seconds
AGGREGATION_RECORD_SIZE = 60        # seconds
AGGREGATOR_SPEC = Bunch(type='Averager')

APPROXIMATE_CHUNK_SIZE = 20000      # sample frames

WORKER_POOL_SIZE = 4                # processes
TASK_SIZE = 50                      # spectra
"""


from multiprocessing import Pool
from pathlib import Path
import time
import wave

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.bunch import Bunch
from vesper.util.data_windows import HannWindow
import vesper.util.time_frequency_analysis_utils as tfa_utils


# TODO: Use signal package to compute spectrograms.
# TODO: Support multichannel recordings.
# TODO: Compute multiple aggregates for the same spectra.
# TODO: Control different aspects of color mapping with different aggregates.


AUDIO_FILE_LOCATIONS = (
    ('internal disk',
        '/Users/harold/Desktop/NFC/2021-11 Aggregate Gram Tests/Audio Files'),
    ('external disk',
        '/Volumes/Recordings1/Nocturnal Bird Migration/Harold/2021/Harold')
)
WORKING_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/2021-11 Aggregate Gram Tests')
AUDIO_FILE_DIR_PATH = WORKING_DIR_PATH / 'Audio Files'
LIST_FILE_PATH = WORKING_DIR_PATH / 'audio_file_names.txt'
GRAM_FILE_PATH = WORKING_DIR_PATH / 'grams.pdf'

WINDOW_SIZE = .040                  # seconds
HOP_SIZE = .020                     # seconds
AGGREGATION_RECORD_SIZE = 60        # seconds
AGGREGATOR_SPEC = Bunch(type='Averager')
# AGGREGATOR_SPEC = Bunch(
#     type='Percentile Aggregator',
#     settings=Bunch(percentile=80))

APPROXIMATE_CHUNK_SIZE = 20000      # sample frames

WORKER_POOL_SIZE = 4                # processes
TASK_SIZE = 50                      # spectra

# Plot power range. 0 to 100 is usually a good starting point.
MIN_PLOT_POWER = 0                  # dB
MAX_PLOT_POWER = 100                # dB

# Matplotlib colormap name, e.g. gray_r, viridis, plasma, inferno, magma,
# cividis
PLOT_COLORMAP = 'cividis'


def main():

    compute_aggregate_grams()

    # time_audio_file_ops(read_audio_file_without_seeks, 'read without seeks')
    # time_audio_file_ops(read_audio_file_with_seeks, 'read with seeks')


def compute_aggregate_grams():

    file_names = get_audio_file_names()

    print(
        'File Location,File Name,File Duration,Computation Time,'
        'Computation Rate')

    for location_name, dir_path in AUDIO_FILE_LOCATIONS:

        dir_path = Path(dir_path)

        with PdfPages(GRAM_FILE_PATH) as pdf:
            
            for file_name in file_names:

                file_path = dir_path / file_name

                start_time = time.time()
                gram, time_step, freq_step = compute_aggregate_gram(file_path)
                end_time = time.time()

                elapsed = end_time - start_time
                duration = gram.shape[0] * time_step
                rate = duration / elapsed
                print(
                    f'{location_name},{file_path.name},{round(duration)},'
                    f'{elapsed:.01f},{round(rate)}')

                plot_aggregate_gram(
                    pdf, gram, time_step, freq_step, file_path.name)


def get_audio_file_paths(location_name):
    dir_paths = dict(p for p in AUDIO_FILE_LOCATIONS)
    dir_path = Path(dir_paths[location_name])
    return [dir_path / n for n in get_audio_file_names()]


def get_audio_file_names():
    with open(LIST_FILE_PATH) as list_file:
        contents = list_file.read()
    lines = [line.strip() for line in contents.strip().split('\n')]
    return [line for line in lines if not line.startswith('#')]


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
            window_size, hop_size, dft_size, AGGREGATOR_SPEC))
        start_spectrum_num += spectrum_count

    freq_step = sample_rate / dft_size

    return tasks, freq_step


def compute_aggregate_spectra(
        file_path, start_spectrum_num, spectrum_count, record_size,
        window_size, hop_size, dft_size, aggregator_spec):

    # print(f'{file_path.name} {start_spectrum_num} {spectrum_count}')

    reader = WaveAudioFileReader(str(file_path))
    window = HannWindow(window_size).samples

    spectrum_size = int(dft_size / 2) + 1
    spectra = np.zeros((spectrum_count, spectrum_size))

    aggregator = create_aggregator(aggregator_spec)

    start_sample_num = start_spectrum_num * record_size

    for i in range(spectrum_count):

        samples = reader.read(start_sample_num, record_size)[0, :]

        gram = compute_spectrogram(samples, window, hop_size, dft_size)

        spectra[i, :] = aggregator.aggregate(gram)

        start_sample_num += record_size

    reader.close()

    tfa_utils.scale_spectrogram(spectra, out=spectra)

    tfa_utils.linear_to_log(spectra, out=spectra)

    return spectra


def create_aggregator(spec):

    cls = _aggregator_classes.get(spec.type)

    if cls is None:
        raise ValueError(f'Unrecognized aggregator type "{spec.type}".')

    if hasattr(spec, 'settings'):
        return cls(spec.settings)
    else:
        return cls()


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


def plot_aggregate_gram(pdf, gram, time_step, freq_step, title):

    plt.figure(figsize=(6, 3))
    
    start_time = 0
    end_time = gram.shape[0] * time_step / 3600
    start_freq = 0
    end_freq = (gram.shape[1] - 1) * freq_step
    extent = (start_time, end_time, start_freq, end_freq)
    
    plt.imshow(
        gram.T, cmap=PLOT_COLORMAP, vmin=MIN_PLOT_POWER, vmax=MAX_PLOT_POWER,
        origin='lower', extent=extent, aspect='auto')
    
    plt.title(title)
    plt.xlabel('Time (hours)')
    plt.ylabel('Frequency (Hz)')
    # plt.ylim(0, 11000)

    pdf.savefig()
    
    plt.close()


def time_audio_file_ops(op, op_name):

    file_names = get_audio_file_names()

    print('Operation,File Location,File Name,Operation Time')

    for location_name, dir_path in AUDIO_FILE_LOCATIONS:

        dir_path = Path(dir_path)

        for file_name in file_names:

            file_path = dir_path / file_name

            start_time = time.time()

            op(file_path)

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f'{op_name},{location_name},{file_name},{elapsed_time:.2f}')


def read_audio_file_without_seeks(file_path):
    with wave.open(str(file_path), 'rb') as reader:
        while True:
            bytes = reader.readframes(1440000)
            byte_count = len(bytes)
            if byte_count == 0:
                break


def read_audio_file_with_seeks(file_path):
    with wave.open(str(file_path), 'rb') as reader:
        pos = 0
        while True:
            reader.setpos(pos)
            bytes = reader.readframes(1440000)
            pos = reader.tell()
            byte_count = len(bytes)
            if byte_count == 0:
                break


class Aggregator:

    name = None

    def aggregate(self, spectra):
        raise NotImplementedError()

        
class Averager(Aggregator):

    name = 'Averager'

    def aggregate(self, spectra):
        return np.average(spectra, axis=0)


class PercentileAggregator(Aggregator):

    name = 'Percentile Aggregator'

    def __init__(self, settings):
        self.percentile = settings.percentile

    def aggregate(self, spectra):
        return np.percentile(spectra, self.percentile, axis=0)


_aggregator_classes = dict(
    (cls.name, cls) for cls in [Averager, PercentileAggregator]
)


if __name__ == '__main__':
    main()
