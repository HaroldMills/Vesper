"""
Script that facilitates comparison of some audio resampling types.

See comments in `main` function for more details.
"""


from pathlib import Path
import time

from matplotlib.backends.backend_pdf import PdfPages
from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import librosa
import soxr

import vesper.util.time_frequency_analysis_utils as tfa_utils


RESULT_DIR_PATH = Path('/Users/harold/Desktop/Resampling Tests')
CROSS_TYPE_QUALITY_PDF_FILE_PATH = \
    RESULT_DIR_PATH / 'Resampling Quality Across Types.pdf'
WITHIN_TYPE_QUALITY_PDF_FILE_PATH = \
    RESULT_DIR_PATH / 'Resampling Quality Within Types.pdf'
WITHIN_TYPE_QUALITY_PDF_FILE_NAME_FORMAT = 'Resampling Quality - {}.pdf'
SIGNAL_STATS_CSV_FILE_PATH = \
    RESULT_DIR_PATH / 'Resampled Signal Stats.csv'
SPEED_PDF_FILE_PATH = RESULT_DIR_PATH / 'Resampling Speed.pdf'
SPEED_STATS_CSV_FILE_PATH = RESULT_DIR_PATH / 'Resampling Speed.csv'

SIGNAL_STATS_CSV_FILE_COLUMN_NAMES = (
    'Name', 'Input Sample Rate (Hz)', 'Output Sample Rate (Hz)',
    'Max Output Sample', 'Min Output Sample', 'RMS Output Sample')

SPEED_STATS_CSV_FILE_COLUMN_NAMES = (
    'Resampling Type', 'Input Sample Rate (Hz)', 'Output Sample Rate (Hz)',
    'Speed (xRT)')

INPUT_SAMPLE_RATES = (
    8000,
    11025,
    16000,
    22050,
    24000,
    24000.1,    # non-integer
    24001,      # prime
    32000,
    44100,
    48000,
    88200,
    96000,
    176400,
    192000,
)

OUTPUT_SAMPLE_RATES = INPUT_SAMPLE_RATES
# OUTPUT_SAMPLE_RATES = (
#     32000,
# )

INCREMENTAL_CHUNK_COUNT = 10


class LibrosaResampler:

    def __init__(self, resampling_type):
        self.resampling_type = resampling_type

    @property
    def name(self):
        return f'Librosa {self.resampling_type}'

    def resample(self, input, input_rate, output_rate):
        return librosa.resample(
            input,
            orig_sr = input_rate,
            target_sr = output_rate,
            res_type = self.resampling_type)
    

class SoxrResampler:

    def __init__(self, quality):
        self.quality = quality

    @property
    def name(self):
        return f'SoXR {self.quality}'
    
    def resample(self, input, input_rate, output_rate):
        return soxr.resample(
            input, input_rate, output_rate, self.quality)


class SoxrIncrementalResampler:

    def __init__(self, quality):
        self.quality = quality

    @property
    def name(self):
        return f'SoXR {self.quality} Inc'
    
    def resample(self, input, input_rate, output_rate):

        r = soxr.ResampleStream(
            input_rate, output_rate, 1, input.dtype, self.quality)
        
        length = len(input)
        chunk_size = length // INCREMENTAL_CHUNK_COUNT

        start_index = 0
        outputs = []

        while start_index != length:

            end_index = start_index + chunk_size

            if end_index >= length:
                end_index = length
                last = True
            else:
                last = False

            chunk = input[start_index:end_index]
            output = r.resample_chunk(chunk, last)
            # output = soxr.resample(
            #     chunk, input_rate, output_rate, self.quality)
            outputs.append(output)

            start_index = end_index

        return np.concatenate(outputs)


# RESAMPLERS = (
#     LibrosaResampler('soxr_vhq'),
#     LibrosaResampler('soxr_hq'),
#     LibrosaResampler('sinc_best'),
#     LibrosaResampler('sinc_medium'),
#     LibrosaResampler('sinc_fastest'),
#     LibrosaResampler('kaiser_best'),
#     LibrosaResampler('kaiser_fast'),
#     LibrosaResampler('fft'),
# )

# RESAMPLER_AXES_INDICES = (
#     (0, 1),
#     (0, 2),
#     (1, 0),
#     (1, 1),
#     (1, 2),
#     (2, 0),
#     (2, 1),
#     (2, 2),
# )

# HIDDEN_AXES_INDICES = ()

RESAMPLERS = (
    SoxrResampler('HQ'),
    SoxrIncrementalResampler('HQ'),
    LibrosaResampler('soxr_hq'),
    SoxrResampler('VHQ'),
    SoxrIncrementalResampler('VHQ'),
    LibrosaResampler('soxr_vhq'),
)

RESAMPLER_AXES_INDICES = (
    (1, 0),
    (1, 1),
    (1, 2),
    (2, 0),
    (2, 1),
    (2, 2),
)

HIDDEN_AXES_INDICES = ((0, 1), (0, 2))

SPEED_TEST_SIGNAL_DURATION = 10
SPEED_TEST_TRIAL_COUNT = 5
SPEED_PLOT_X_LIMIT = 20000


def main():

    # Create PDF file of spectrograms arranged to facilitate across-type
    # comparison of resampling quality. Also write resampled signal
    # statistics to a CSV file.
    compare_resampling_quality_across_types()

    # Create PDF files of spectrograms arranged to facilitate within-type
    # evaluation of resampling quality.
    compare_resampling_quality_within_types()

    # Create PDF file of bar charts comparing resampling speeds across
    # resampling type. Also write speeds to a CSV file.
    measure_resampling_speed()


def compare_resampling_quality_across_types():

    inputs = create_quality_test_inputs()
    signal_stats = []

    with PdfPages(CROSS_TYPE_QUALITY_PDF_FILE_PATH) as pdf_file:

        for output_rate in OUTPUT_SAMPLE_RATES:

            for input_rate in INPUT_SAMPLE_RATES:

                if rate_pair_enabled(input_rate, output_rate):

                    print(
                        f'Testing {input_rate} Hz to {output_rate} Hz '
                        f'quality...')
                    
                    compare_resampling_quality_across_types_aux(
                        inputs, input_rate, output_rate, pdf_file,
                        signal_stats)
                    
    write_signal_stats_csv_file(signal_stats)


def compare_resampling_quality_across_types_aux(
        inputs, input_rate, output_rate, pdf_file, signal_stats):
    
    input = inputs[input_rate]

    _, axes = plt.subplots(3, 3)
    for i, j in HIDDEN_AXES_INDICES:
        axes[i][j].set_visible(False)

    plt.suptitle(f'{input_rate} Hz to {output_rate} Hz')

    stats = get_signal_stats('input', input_rate, output_rate, input)
    signal_stats.append(stats)

    plot_spectrogram(
        input, input_rate, output_rate, 'Input', False, axes[0, 0])

    for index, resampler in enumerate(RESAMPLERS):

        # Resample.
        output = resampler.resample(input, input_rate, output_rate)

        stats = \
            get_signal_stats(resampler.name, input_rate, output_rate, output)
        signal_stats.append(stats)

        # Get subplot indices.
        i, j = RESAMPLER_AXES_INDICES[index]

        plot_spectrogram(
            output, output_rate, output_rate, resampler.name, False,
            axes[i][j])

    plt.tight_layout()

    pdf_file.savefig()
    
    plt.close()


def get_signal_stats(name, input_rate, output_rate, samples):
    
    max_sample = int(round(np.max(samples)))
    min_sample = int(round(np.min(samples)))

    # Use double precision to compute RMS sample valuew to avoid overflow.
    x = samples.astype('float64')
    rms_sample = int(round(np.sqrt(np.sum(x * x) / len(samples))))
    
    return (name, input_rate, output_rate, max_sample, min_sample, rms_sample)


def compare_resampling_quality_within_types():

    inputs = create_quality_test_inputs()

    # for resampling_type in RESAMPLING_TYPES:

    #     print(f'Testing {resampling_type} quality...')

    #     file_name = \
    #         WITHIN_TYPE_QUALITY_PDF_FILE_NAME_FORMAT.format(resampling_type)
    #     file_path = RESULT_DIR_PATH / file_name

    #     with PdfPages(file_path) as pdf_file:

    with PdfPages(WITHIN_TYPE_QUALITY_PDF_FILE_PATH) as pdf_file:

        for resampler in RESAMPLERS:

            print(f'Testing {resampler.name} quality...')

            for output_rate in OUTPUT_SAMPLE_RATES:

                for input_rate in INPUT_SAMPLE_RATES:

                    if rate_pair_enabled(input_rate, output_rate):

                        compare_resampling_quality_within_types_aux(
                            inputs, input_rate, output_rate, resampler,
                            pdf_file)
    
    
def compare_resampling_quality_within_types_aux(
        inputs, input_rate, output_rate, resampler, pdf_file):
    
    input = inputs[input_rate]

    # Resample.
    output = resampler.resample(input, input_rate, output_rate)
    
    _, axes = plt.subplots(2, 1)

    plt.suptitle(f'{resampler.name} - {input_rate} Hz to {output_rate} Hz')
    plot_spectrogram(input, input_rate, output_rate, 'Input', True, axes[0])
    plot_spectrogram(output, output_rate, output_rate, 'Output', True, axes[1])
    plt.tight_layout()

    pdf_file.savefig()
    
    plt.close()


def create_quality_test_inputs():
    return {
        sample_rate: create_quality_test_input(sample_rate)
        for sample_rate in INPUT_SAMPLE_RATES}
    

def create_quality_test_input(sample_rate):
    
    amplitude = 15000
    duration = 5
    taper_duration = .05
    
    # Create sine.
    # freq = 8000
    # sine = create_sine(
    #     sample_rate, np.float32, amplitude, freq, duration, taper_duration)
    
    # Create chirp.
    start_freq = 0
    end_freq = sample_rate / 2
    chirp = create_chirp(
        sample_rate, np.float32, amplitude, start_freq, end_freq, duration,
        taper_duration)
    
    # Sum.
    # samples = sine + chirp
    samples = chirp
    
    # Scale to desired overall amplitude.
    overall_amplitude = 30000
    samples *= overall_amplitude / np.max(np.abs(samples))
    
    # Round samples to nearest integers.
    samples = np.round(samples)
    
    return samples
    
    
def create_sine(
        sample_rate, sample_dtype, amplitude, freq, duration, taper_duration):
    
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    phases = 2 * np.pi * freq * times
    sine = amplitude * np.sin(phases)
    
    taper_ends(sine, sample_rate, taper_duration)
    
    return sine.astype(sample_dtype)
    
    
def taper_ends(samples, sample_rate, taper_duration):
    
    # Taper ends.
    taper_length = int(round(taper_duration * sample_rate))
    taper = np.arange(taper_length) / float(taper_length)
    samples[:taper_length] *= taper
    samples[-taper_length:] *= 1 - taper
    
    return samples


def create_chirp(
        sample_rate, sample_dtype, amplitude, start_freq, end_freq, duration,
        taper_duration):
    
    # Compute chirp.
    length = round(duration * sample_rate)
    times = np.arange(length) / sample_rate
    delta_freq = end_freq - start_freq
    freqs = start_freq + delta_freq * times / (2 * duration)
    phases = 2. * np.pi * freqs * times
    chirp = amplitude * np.sin(phases)
    
    taper_ends(chirp, sample_rate, taper_duration)
    
    return chirp.astype(sample_dtype)


def rate_pair_enabled(input_rate, output_rate):
    return input_rate != output_rate


def plot_spectrogram(
        samples, sample_rate, output_rate, title, include_axes, axes):
    
    '''
    `sample_rate` is sample rate of `samples`, either input or output rate.
    `output_rate` is resampling output rate.
    '''

    window_size_sec = .005
    hop_size_percent = 20
    
    window_size = int(round(window_size_sec * sample_rate))
    window = signal.hann(window_size, sym=False)
    hop_size = \
        int(round(window_size_sec * hop_size_percent / 100 * sample_rate))
        
    dft_size = 2 * tfa_utils.get_dft_size(window_size)
    
    gram = tfa_utils.compute_spectrogram(samples, window, hop_size, dft_size)
    
    gram = tfa_utils.linear_to_log(gram)
    
    # plot_histogram(gram)
    
    hop_size_sec = window_size_sec * hop_size_percent / 100
    times = np.arange(len(gram)) * hop_size_sec + window_size_sec / 2
    
    num_bins = dft_size / 2 + 1
    bin_size = sample_rate / dft_size
    freqs = np.arange(num_bins) * bin_size
        
    x = gram.transpose()
    
    # plt.figure(figsize=(12, 6))
        
    start_time = times[0] - hop_size_sec / 2
    end_time = times[-1] + hop_size_sec / 2
    start_freq = freqs[0]
    end_freq = freqs[-1]
    extent = (start_time, end_time, start_freq, end_freq)
    
    # `vmin` and `vmax` were chosen by looking at histogram of spectrogram
    # values plotted by `plot_histogram` function.
    # colormap_name = 'gray_r'
    colormap_name = 'viridis'
    image = axes.imshow(
        x, cmap=colormap_name, vmin=-25, vmax=125, origin='lower',
        extent=extent, aspect='auto')
    
    axes.set_title(title)
    axes.set_ylim(0, output_rate / 2)

    if include_axes:
        axes.set_xlabel('Time (s)')
        axes.set_ylabel('Frequency (Hz)')
        plt.colorbar(image, label='Power (dB)')

    else:
        axes.get_xaxis().set_visible(False)
        axes.get_yaxis().set_visible(False)


def plot_histogram(x):
    
    num_bins = 300
    min_value = -100
    max_value = 200
    
    histogram, edges = np.histogram(x, num_bins, (min_value, max_value))
    distribution = histogram / histogram.sum()
    
#     bin_size = (max_value - min_value) / num_bins
#     edges = min_value + np.arange(num_bins + 1) * bin_size
    
    plt.figure(1)
    plt.plot(edges[:-1], distribution)
    plt.xlim((edges[0], edges[-1]))
    plt.title('Distribution of Spectrogram Values')
    plt.xlabel('Log Power')
    plt.show()
    
    
def write_signal_stats_csv_file(signal_stats):
    with open(SIGNAL_STATS_CSV_FILE_PATH, 'wt') as file:
        write_csv_file_line(file, SIGNAL_STATS_CSV_FILE_COLUMN_NAMES)
        for stats in signal_stats:
            write_csv_file_line(file, stats)


def write_csv_file_line(file, items):
    line = ','.join(str(i) for i in items) + '\n'
    file.write(line)
    

def measure_resampling_speed():

    speed_stats = []

    with PdfPages(SPEED_PDF_FILE_PATH) as pdf_file:

        for output_rate in OUTPUT_SAMPLE_RATES:

            for input_rate in INPUT_SAMPLE_RATES:

                if rate_pair_enabled(input_rate, output_rate):

                    print(
                        f'Testing {input_rate} Hz to {output_rate} Hz '
                        f'speed...')
                    
                    measure_resampling_speed_aux(
                        input_rate, output_rate, pdf_file, speed_stats)
                    
    write_speed_stats_csv_file(speed_stats)


def measure_resampling_speed_aux(
        input_rate, output_rate, pdf_file, speed_stats):
        
    samples = create_speed_test_signal(input_rate)
    speeds = np.zeros(len(RESAMPLERS))

    for i, resampler in enumerate(RESAMPLERS):
        stats = time_resampling(samples, input_rate, output_rate, resampler)
        speed_stats.append(stats)
        speeds[i] = stats[-1]

    plot_speeds(speeds, input_rate, output_rate, pdf_file)


def create_speed_test_signal(sample_rate):
    n = int(round(SPEED_TEST_SIGNAL_DURATION * sample_rate))
    return np.random.randn(n)
    
    
def time_resampling(samples, input_rate, output_rate, resampler):

    elapsed_times = np.zeros(SPEED_TEST_TRIAL_COUNT)
    
    for i in range(SPEED_TEST_TRIAL_COUNT):
        start_time = time.time()
        resampler.resample(samples, input_rate, output_rate)
        elapsed_times[i] = time.time() - start_time
        
    # speeds = SPEED_TEST_SIGNAL_DURATION / elapsed_times
    # print('Speeds for all trials:', speeds)

    min_elapsed_time = np.min(elapsed_times)
    speed = int(round(SPEED_TEST_SIGNAL_DURATION / min_elapsed_time))
    # print(
    #     f'Fastest trial resampled {SPEED_TEST_SIGNAL_DURATION} seconds '
    #     f'of audio in {min_elapsed_time:.1f} seconds, {speed} times '
    #     f'faster than real time.')
    
    return resampler.name, input_rate, output_rate, speed

    
def plot_speeds(speeds, input_rate, output_rate, pdf_file):
            
    # bars
    ys = np.arange(len(speeds))
    bars = plt.barh(ys, speeds)
    plt.bar_label(bars)

    # title
    title = f'Librosa Resampling Speed - {input_rate} Hz to {output_rate} Hz'
    plt.title(title)

    # y axis
    plt.ylabel('Resampling Type')
    names = [r.name for r in RESAMPLERS]
    plt.yticks(ys, names)
    plt.gca().invert_yaxis()

    # x axis
    plt.xlabel('Speed (times faster than real time)')
    plt.xlim(right=SPEED_PLOT_X_LIMIT)

    plt.tight_layout()

    pdf_file.savefig()

    plt.close()
            

def write_speed_stats_csv_file(speed_stats):
    with open(SPEED_STATS_CSV_FILE_PATH, 'wt') as file:
        write_csv_file_line(file, SPEED_STATS_CSV_FILE_COLUMN_NAMES)
        for stats in speed_stats:
            write_csv_file_line(file, stats)
    

if __name__ == '__main__':
    main()
