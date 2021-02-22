"""
Script that computes and displays audio recording statistics.

The statistics computed for a recording include an *ampligram*. An
ampligram is an image whose X axis is time, whose Y axis is waveform
amplitude, and in which color indicates the sample count in a particular
time/amplitude cell. It is useful for assessing the gain setting of a
recording, since it illustrates how much of the available amplitude
dynamic range the recording uses, and how often there is clipping in the
recording.

An ampligram can be *one-sided* or *two-sided*. A one-sided ampligram
plots counts of absolute sample values, and its Y axis ranges from zero
(the minimum absolute sample value) to one (the maximum absolute sample
value). A two-sided ampligram plots counts of non-absolute sample values,
and its Y axis ranges from minus one (the minimum sample value) to one
(the maximum sample value).
"""


from collections import defaultdict
from pathlib import Path
import math
import time

from matplotlib import cm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt
import numpy as np

from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.util.bunch import Bunch


TEST_MODE_ENABLED = False
TEST_MODE_INTERVAL_COUNT_LIMIT = 50

# RECORDING_DIR_PATH = \
#     Path('/Volumes/Recordings2/Nocturnal Bird Migration/Harold/2020')
#     
# RECORDING_FILE_NAMES = (
#     
#     ('Harold_2020-10-18_23.18.22_Z.wav',),
#     ('Harold_2020-10-19_23.16.50_Z.wav',),
#     ('Harold_2020-10-20_23.15.18_Z.wav',),
#     ('Harold_2020-10-21_23.13.48_Z.wav',),
#     ('Harold_2020-10-22_23.12.18_Z.wav',),
#     ('Harold_2020-10-23_23.10.49_Z.wav',),
#     ('Harold_2020-10-24_23.09.22_Z.wav',),
#     ('Harold_2020-10-25_23.07.56_Z.wav',),
#     ('Harold_2020-10-26_23.06.31_Z.wav',),
#     ('Harold_2020-10-27_23.05.08_Z.wav',),
#     ('Harold_2020-10-28_23.03.45_Z.wav',),
#     ('Harold_2020-10-29_23.02.24_Z.wav',),
#     ('Harold_2020-10-30_23.01.04_Z.wav',),
#     ('Harold_2020-10-31_22.59.45_Z.wav',),
# 
# #     ('Harold2_2020-11-04_22.54.47_Z.wav',
# #      'Harold2_2020-11-05_03.34.24_Z.wav',
# #      'Harold2_2020-11-05_08.14.00_Z.wav',),
#     
# )

# RECORDING_DIR_PATH = \
#     Path('/Volumes/MPG Ranch 2018 Part 2/09/MPG Floodplain')
#     
# RECORDING_FILE_NAMES = (
#     ('FLOOD-21C_20180901_194500.wav',),
#     ('FLOOD-21C_20180902_194400.wav',),
#     ('FLOOD-21C_20180903_194200.wav',),
#     ('FLOOD-21C_20180904_194000.wav',),
#     ('FLOOD-21C_20180905_193800.wav',),
#     ('FLOOD-21C_20180906_193600.wav',),
#     ('FLOOD-21C_20180907_193400.wav',),
#     ('FLOOD-21C_20180908_193200.wav',),
#     ('FLOOD-21C_20180909_193000.wav',),
#     ('FLOOD-21C_20180910_192800.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-06')
#     
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-07_00.30.00_Z.wav',
#      'usny000_2000-05-07_01.30.01_Z.wav',
#      'usny000_2000-05-07_02.30.01_Z.wav',
#      'usny000_2000-05-07_03.30.01_Z.wav',
#      'usny000_2000-05-07_04.30.01_Z.wav',
#      'usny000_2000-05-07_05.30.01_Z.wav',
#      'usny000_2000-05-07_06.30.01_Z.wav',
#      'usny000_2000-05-07_07.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-07')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-08_00.30.00_Z.wav',
#      'usny000_2000-05-08_01.30.01_Z.wav',
#      'usny000_2000-05-08_02.30.01_Z.wav',
#      'usny000_2000-05-08_03.30.01_Z.wav',
#      'usny000_2000-05-08_04.30.01_Z.wav',
#      'usny000_2000-05-08_05.30.01_Z.wav',
#      'usny000_2000-05-08_06.30.01_Z.wav',
#      'usny000_2000-05-08_07.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-08')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-09_00.30.00_Z.wav',
#      'usny000_2000-05-09_01.30.00_Z.wav',
#      'usny000_2000-05-09_02.30.00_Z.wav',
#      'usny000_2000-05-09_03.30.00_Z.wav',
#      'usny000_2000-05-09_04.30.00_Z.wav',
#      'usny000_2000-05-09_05.30.00_Z.wav',
#      'usny000_2000-05-09_06.30.00_Z.wav',
#      'usny000_2000-05-09_07.30.00_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-10')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-11_00.30.00_Z.wav',
#      'usny000_2000-05-11_01.30.01_Z.wav',
#      'usny000_2000-05-11_02.30.01_Z.wav',
#      'usny000_2000-05-11_03.30.01_Z.wav',
#      'usny000_2000-05-11_04.30.01_Z.wav',
#      'usny000_2000-05-11_05.30.01_Z.wav',
#      'usny000_2000-05-11_06.30.01_Z.wav',
#      'usny000_2000-05-11_07.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-11')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-12_00.30.00_Z.wav',
#      'usny000_2000-05-12_01.30.01_Z.wav',
#      'usny000_2000-05-12_02.30.01_Z.wav',
#      'usny000_2000-05-12_03.30.01_Z.wav',
#      'usny000_2000-05-12_04.30.01_Z.wav',
#      'usny000_2000-05-12_05.30.01_Z.wav',
#      'usny000_2000-05-12_06.30.01_Z.wav',
#      'usny000_2000-05-12_07.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-05-12')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-05-13_00.30.00_Z.wav',
#      'usny000_2000-05-13_01.30.01_Z.wav',
#      'usny000_2000-05-13_02.30.01_Z.wav',
#      'usny000_2000-05-13_03.30.01_Z.wav',
#      'usny000_2000-05-13_04.30.01_Z.wav',
#      'usny000_2000-05-13_05.30.01_Z.wav',
#      'usny000_2000-05-13_06.30.01_Z.wav',
#      'usny000_2000-05-13_07.30.01_Z.wav',
#      'usny000_2000-05-13_08.30.01_Z.wav',
#      'usny000_2000-05-13_09.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-09-22')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-09-23_01.30.00_Z.wav',
#      'usny000_2000-09-23_02.30.01_Z.wav',
#      'usny000_2000-09-23_03.30.01_Z.wav',
#      'usny000_2000-09-23_04.30.01_Z.wav',
#      'usny000_2000-09-23_05.30.01_Z.wav',
#      'usny000_2000-09-23_06.30.01_Z.wav',
#      'usny000_2000-09-23_07.30.01_Z.wav',
#      'usny000_2000-09-23_08.30.01_Z.wav',
#      'usny000_2000-09-23_09.30.01_Z.wav',),
# )
 
# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-09-23')
#      
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-09-24_01.30.00_Z.wav',
#      'usny000_2000-09-24_02.30.01_Z.wav',
#      'usny000_2000-09-24_03.30.01_Z.wav',
#      'usny000_2000-09-24_04.30.01_Z.wav',
#      'usny000_2000-09-24_05.30.01_Z.wav',
#      'usny000_2000-09-24_06.30.01_Z.wav',
#      'usny000_2000-09-24_07.30.01_Z.wav',
#      'usny000_2000-09-24_08.30.01_Z.wav',
#      'usny000_2000-09-24_09.30.01_Z.wav',
#      'usny000_2000-09-24_10.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-09-25')
#       
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-09-26_01.30.00_Z.wav',
#      'usny000_2000-09-26_02.30.01_Z.wav',
#      'usny000_2000-09-26_03.30.01_Z.wav',
#      'usny000_2000-09-26_04.30.01_Z.wav',
#      'usny000_2000-09-26_05.30.01_Z.wav',
#      'usny000_2000-09-26_06.30.01_Z.wav',
#      'usny000_2000-09-26_07.30.01_Z.wav',
#      'usny000_2000-09-26_08.30.01_Z.wav',
#      'usny000_2000-09-26_09.30.01_Z.wav',
#      'usny000_2000-09-26_10.30.01_Z.wav',),
# )

# RECORDING_DIR_PATH = \
#     Path(
#         '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
#         '2000-09-26')
#       
# RECORDING_FILE_NAMES = (
#     ('usny000_2000-09-27_01.30.00_Z.wav',
#      'usny000_2000-09-27_02.30.01_Z.wav',
#      'usny000_2000-09-27_03.30.01_Z.wav',
#      'usny000_2000-09-27_04.30.01_Z.wav',
#      'usny000_2000-09-27_05.30.01_Z.wav',
#      'usny000_2000-09-27_06.30.01_Z.wav',
#      'usny000_2000-09-27_07.30.01_Z.wav',
#      'usny000_2000-09-27_08.30.01_Z.wav',
#      'usny000_2000-09-27_09.30.01_Z.wav',
#      'usny000_2000-09-27_10.30.01_Z.wav',),
# )

RECORDING_DIR_PATH = \
    Path(
        '/Volumes/Recordings2/Nocturnal Bird Migration/BirdCast 2000/'
        '2000-09-27')
      
RECORDING_FILE_NAMES = (
    ('usny000_2000-09-28_01.30.00_Z.wav',
     'usny000_2000-09-28_02.30.01_Z.wav',
     'usny000_2000-09-28_03.30.01_Z.wav',
     'usny000_2000-09-28_04.30.01_Z.wav',
     'usny000_2000-09-28_05.30.01_Z.wav',
     'usny000_2000-09-28_06.30.01_Z.wav',
     'usny000_2000-09-28_07.30.01_Z.wav',
     'usny000_2000-09-28_08.30.01_Z.wav',
     'usny000_2000-09-28_09.30.01_Z.wav',
     'usny000_2000-09-28_10.30.01_Z.wav',),
)

OUTPUT_DIR_PATH = Path('/Users/harold/Desktop/Recording Stats')
AMPLIGRAM_PLOT_FILE_NAME_FORMAT = '{} Ampligram.pdf'

INTERVAL_DURATION = 60

MAX_ABS_SAMPLE = 32768

AMPLIGRAM_ONE_SIDED = True
AMPLIGRAM_BIN_COUNT = 100
AMPLIGRAM_COLORMAP_MIN_VALUE = 1e-7    # set to about fraction for one sample 
AMPLIGRAM_COLORMAP_MAX_VALUE = 1
AMPLIGRAM_COLORMAP_NAME = 'inferno'
AMPLIGRAM_COLORMAP_BAD_COLOR = 'white'

PROGRESS_MESSAGE_PERIOD = 100


# TODO: Write statistics to CSV files, one per recording.


def main():
    
    start_time = time.time()
    
    for file_paths in get_recording_file_paths():
        show_recording_interval_stats(file_paths, INTERVAL_DURATION)
        
    end_time = time.time()
    duration = end_time - start_time
    print(f'Processing took {duration} seconds.')
    
    
def get_recording_file_paths():
    return [
        get_recording_file_paths_aux(file_names)
        for file_names in RECORDING_FILE_NAMES]
    
    
def get_recording_file_paths_aux(file_names):
    if TEST_MODE_ENABLED:
        return [RECORDING_DIR_PATH / file_names[0]]
    else:
        return [RECORDING_DIR_PATH / file_name for file_name in file_names]


def show_recording_interval_stats(file_paths, interval_duration):
    stats = get_recording_stats(file_paths, interval_duration)
    recording_name = get_recording_name(file_paths)
    plot_ampligram(recording_name, stats)
    
    
def get_recording_stats(file_paths, interval_duration):
    
    file_count = len(file_paths)
    file_stats = []
    for file_num, file_path in enumerate(file_paths):
        print(f'File "{file_path.name}", {file_num + 1} of {file_count}...')
        stats = get_file_interval_stats(file_path, interval_duration)
        file_stats.append(stats)
    
    # file_stats[file_num][channel_num][interval_num] is a stat dict
    
    file_count = len(file_stats)
    channel_count = len(file_stats[0])
    channel_stats = [defaultdict(list) for _ in range(channel_count)]
    for file_num in range(file_count):
        for channel_num in range(channel_count):
            interval_stats = file_stats[file_num][channel_num]
            for stat_dict in interval_stats:
                for name in [
                        'max', 'min', 'mean', 'mean_abs', 'std', 'ampligram']:
                    channel_stats[channel_num][name].append(stat_dict[name])
                    
    # channel_stats[channel_num] is a defaultdict of stat lists
            
    recording_stats = [create_channel_stat_bunch(s) for s in channel_stats]

    # recording_stats[channel_num] is a stat bunch
    
    return recording_stats
    

def get_file_interval_stats(file_path, interval_duration):
    
    reader = WaveAudioFileReader(str(file_path))
    channel_count = reader.num_channels
    interval_length = int(interval_duration * reader.sample_rate)
    
    interval_count = reader.length // interval_length
    if TEST_MODE_ENABLED:
        interval_count = min(interval_count, TEST_MODE_INTERVAL_COUNT_LIMIT)
    
    stats = [[] for _ in range(channel_count)]
    
    for interval_num in range(interval_count):
        
        if interval_num != 0 and interval_num % PROGRESS_MESSAGE_PERIOD == 0:
            print(f'    Interval {interval_num} of {interval_count}...')
        
        stat_computers = [
            StatComputer(AMPLIGRAM_ONE_SIDED, AMPLIGRAM_BIN_COUNT)
            for _ in range(channel_count)]
    
        frame_num = interval_num * interval_length
        samples = reader.read(frame_num, interval_length) / MAX_ABS_SAMPLE
        
        for channel_num in range(channel_count):
            computer = stat_computers[channel_num]
            computer.process_samples(samples[channel_num])
            stats[channel_num].append(computer.get_stats())
    
    return stats
    
    
def create_channel_stat_bunch(stat_dicts):
    return Bunch(
        max=np.array(stat_dicts['max']),
        min=np.array(stat_dicts['min']),
        mean=np.array(stat_dicts['mean']),
        mean_abs=np.array(stat_dicts['mean_abs']),
        std=np.array(stat_dicts['std']),
        ampligram=np.stack(stat_dicts['ampligram']))
    
    
def get_recording_name(file_paths):
    return file_paths[0].name[:-4]


def plot_ampligram(recording_name, recording_stats):
    
    pdf_file_path = get_ampligram_file_path(recording_name)
    
    with PdfPages(pdf_file_path) as pdf:

        channel_count = len(recording_stats)
        
        figure, axes_list = plt.subplots(channel_count, figsize=(9, 6))
        
        # When there's only one channel, `axes_list` is an `AxesSubplot`
        # rather than a sequence of them.
        if channel_count == 1:
            axes_list = [axes_list]
        
        for channel_num, channel_stats in enumerate(recording_stats):
            
            print(f'channel {channel_num}:')
            print(f'max {channel_stats.max}')
            print(f'min {channel_stats.min}')
            print(f'mean {channel_stats.mean}')
            print(f'mean_abs {channel_stats.mean_abs}')
            print(f'std {channel_stats.std}')
            
            gram = channel_stats.ampligram.transpose()

            start_time = 0
            end_time = gram.shape[1] / 60
            start_amp, end_amp = StatComputer.get_ampligram_amplitude_range(
                AMPLIGRAM_ONE_SIDED)
            extent = (start_time, end_time, start_amp, end_amp)
            
            colormap = cm.get_cmap(AMPLIGRAM_COLORMAP_NAME)
            colormap.set_bad(AMPLIGRAM_COLORMAP_BAD_COLOR)
            colormap_norm = LogNorm(
                vmin=AMPLIGRAM_COLORMAP_MIN_VALUE,
                vmax=AMPLIGRAM_COLORMAP_MAX_VALUE,
                clip=True)
            
            axes = axes_list[channel_num]
            
            image = axes.imshow(
                gram, cmap=colormap, norm=colormap_norm,
                origin='lower', extent=extent, aspect='auto',
                interpolation='nearest')
            
            axes.set_xlabel('Time (hours)')
            axes.set_ylabel('Amplitude')
            axes.label_outer()
        
        figure.suptitle(f'{recording_name} Ampligram')
        colorbar = figure.colorbar(image, ax=axes_list)
        colorbar.ax.set_ylabel('Fraction of Samples')
        
        # This messed up the layout as of 2020-11-06.
        # plt.tight_layout()
        
        pdf.savefig()
        plt.close()
    
    
def get_ampligram_file_path(recording_name):
    file_name = AMPLIGRAM_PLOT_FILE_NAME_FORMAT.format(recording_name)
    return OUTPUT_DIR_PATH / file_name


_DEFAULT_ONE_SIDED_AMPLIGRAM_BIN_COUNT = 100


class StatComputer:
    
    
    @staticmethod
    def get_ampligram_amplitude_range(ampligram_one_sided):
        if ampligram_one_sided:
            return (0, 1)
        else:
            return (-1, 1)
        
        

    def __init__(self, ampligram_one_sided=True, ampligram_bin_count=None):
        
        self._sample_count = 0
        self._max = -1
        self._min = 1
        self._sum = 0
        self._abs_sum = 0
        self._squared_sum = 0
        
        self._ampligram_one_sided = ampligram_one_sided
        self._ampligram_amplitude_range = \
            StatComputer.get_ampligram_amplitude_range(ampligram_one_sided)
        self._ampligram_bin_count = \
            self._get_ampligram_bin_count(ampligram_bin_count)
        self._hist = np.zeros(self._ampligram_bin_count, dtype='int')
        
        
    def _get_ampligram_bin_count(self, ampligram_bin_count):
        
        if ampligram_bin_count is None:
            # bin count not specified
            
            if self._ampligram_one_sided:
                return _DEFAULT_ONE_SIDED_AMPLIGRAM_BIN_COUNT
            else:
                return 2 * _DEFAULT_ONE_SIDED_AMPLIGRAM_BIN_COUNT + 1
            
        else:
            # bin count specified
            
            return ampligram_bin_count
            
            
    def process_samples(self, samples):
        self._sample_count += len(samples)
        self._max = max(self._max, samples.max())
        self._min = min(self._min, samples.min())
        self._sum += samples.sum()
        self._abs_sum += np.abs(samples).sum()
        self._squared_sum += (samples * samples).sum()
        self._hist += self._compute_histogram(samples)
        
        
    def _compute_histogram(self, samples):
        
        if self._ampligram_one_sided:
            samples = np.abs(samples)
            
        hist, _ = np.histogram(
            samples, self._ampligram_bin_count,
            self._ampligram_amplitude_range)
        
        return hist
        
        
    def get_stats(self):
        
        mean = self._sum / self._sample_count
        mean_abs = self._abs_sum / self._sample_count
        std = math.sqrt(self._squared_sum / self._sample_count)
        ampligram = self._hist / self._sample_count
        
        return {
            'sample_count': self._sample_count,
            'max': self._max,
            'min': self._min,
            'mean': mean,
            'mean_abs': mean_abs,
            'std': std,
            'ampligram': ampligram
        }
        
        
if __name__ == '__main__':
    main()
