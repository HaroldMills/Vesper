"""
Script that facilitates comparison of different librosa resampling types.

See comments in `main` function for more details.
"""


from pathlib import Path
import time

from matplotlib.backends.backend_pdf import PdfPages
from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import librosa

import vesper.util.time_frequency_analysis_utils as tfa_utils


RESULT_DIR_PATH = Path('/Users/harold/Desktop/Librosa Resampling Tests')
QUALITY_PDF_FILE_PATH_A = RESULT_DIR_PATH / 'Librosa Resampling Quality A.pdf'
QUALITY_PDF_FILE_PATH_B = RESULT_DIR_PATH / 'Librosa Resampling Quality B.pdf'
SIGNAL_STATS_CSV_FILE_PATH = \
    RESULT_DIR_PATH / 'Librosa Resampled Signal Stats.csv'
SPEED_PDF_FILE_PATH = RESULT_DIR_PATH / 'Librosa Resampling Speed.pdf'
SPEED_STATS_CSV_FILE_PATH = RESULT_DIR_PATH / 'Librosa Resampling Speed.csv'

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

# OUTPUT_SAMPLE_RATES = INPUT_SAMPLE_RATES
OUTPUT_SAMPLE_RATES = (
    32000,
)

RESAMPLING_TYPES = (
    'soxr_vhq',
    'soxr_hq',
    'sinc_best',
    'sinc_medium',
    'sinc_fastest',
    'kaiser_best',
    'kaiser_fast',
    'fft',
)

DURATION = 10
NUM_TRIALS = 5


def main():

    # Create PDF file of spectrograms arranged to facilitate across-type
    # comparison of resampling quality. Also write resampled signal
    # statistics to a CSV file.
    test_resampling_quality_a()

    # Create PDF file of spectrograms arranged to facilitate within-type
    # evaluation of resampling quality.
    test_resampling_quality_b()

    # Create PDF file of bar charts comparing resampling speeds across
    # resampling type. Also write speeds to a CSV file.
    test_resampling_speed()


def test_resampling_quality_a():

    inputs = create_quality_test_inputs()
    signal_stats = []

    with PdfPages(QUALITY_PDF_FILE_PATH_A) as pdf_file:
        for output_rate in OUTPUT_SAMPLE_RATES:
            for input_rate in INPUT_SAMPLE_RATES:
                if rate_pair_enabled(input_rate, output_rate):

                    print(
                        f'Testing {input_rate} Hz to {output_rate} Hz '
                        f'quality...')
                    
                    test_resampling_quality_a_aux(
                        inputs, input_rate, output_rate, pdf_file,
                        signal_stats)
                    
    write_signal_stats_csv_file(signal_stats)


def test_resampling_quality_a_aux(
        inputs, input_rate, output_rate, pdf_file, signal_stats):
    
    input = inputs[input_rate]

    _, axes = plt.subplots(3, 3)

    plt.suptitle(f'{input_rate} Hz to {output_rate} Hz')

    stats = get_signal_stats('input', input_rate, output_rate, input)
    signal_stats.append(stats)

    plot_spectrogram(
        input, input_rate, output_rate, 'Input', False, axes[0, 0])

    for index, resampling_type in enumerate(RESAMPLING_TYPES):

        # Resample.
        output = librosa.resample(
            input,
            orig_sr = input_rate,
            target_sr = output_rate,
            res_type = resampling_type)

        stats = \
            get_signal_stats(resampling_type, input_rate, output_rate, output)
        signal_stats.append(stats)

        # Get subplot indices.
        k = index + 1
        i = k // 3
        j = k % 3

        plot_spectrogram(
            output, output_rate, output_rate, resampling_type, False,
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


def test_resampling_quality_b():
    inputs = create_quality_test_inputs()
    with PdfPages(QUALITY_PDF_FILE_PATH_B) as pdf_file:
        for resampling_type in RESAMPLING_TYPES:
            print(f'Testing {resampling_type} quality...')
            for output_rate in OUTPUT_SAMPLE_RATES:
                for input_rate in INPUT_SAMPLE_RATES:
                    if rate_pair_enabled(input_rate, output_rate):
                        test_resampling_quality_b_aux(
                            inputs, input_rate, output_rate, resampling_type,
                            pdf_file)
    
    
def test_resampling_quality_b_aux(
        inputs, input_rate, output_rate, resampling_type, pdf_file):
    
    input = inputs[input_rate]

    # Resample.
    output = librosa.resample(
        input,
        orig_sr = input_rate,
        target_sr = output_rate,
        res_type = resampling_type)
    
    _, axes = plt.subplots(2, 1)

    plt.suptitle(f'{resampling_type} - {input_rate} Hz to {output_rate} Hz')
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
    

def test_resampling_speed():

    speed_stats = []

    with PdfPages(SPEED_PDF_FILE_PATH) as pdf_file:
        for output_rate in OUTPUT_SAMPLE_RATES:
            for input_rate in INPUT_SAMPLE_RATES:
                if rate_pair_enabled(input_rate, output_rate):

                    print(
                        f'Testing {input_rate} Hz to {output_rate} Hz '
                        f'speed...')
                    
                    test_resampling_speed_aux(
                        input_rate, output_rate, pdf_file, speed_stats)
                    
    write_speed_stats_csv_file(speed_stats)


def test_resampling_speed_aux(input_rate, output_rate, pdf_file, speed_stats):
        
    samples = create_speed_test_signal(input_rate)
    speeds = np.zeros(len(RESAMPLING_TYPES))

    for i, resampling_type in enumerate(RESAMPLING_TYPES):
        stats = time_resampling(
            samples, input_rate, output_rate, resampling_type)
        speed_stats.append(stats)
        speeds[i] = stats[-1]

    plot_speeds(speeds, input_rate, output_rate, pdf_file)


def create_speed_test_signal(sample_rate):
    n = int(round(DURATION * sample_rate))
    return np.random.randn(n)
    
    
def time_resampling(samples, input_rate, output_rate, resampling_type):

    elapsed_times = np.zeros(NUM_TRIALS)
    
    for i in range(NUM_TRIALS):

        start_time = time.time()

        librosa.resample(
            samples, orig_sr=input_rate, target_sr=output_rate,
            res_type=resampling_type)
        
        elapsed_times[i] = time.time() - start_time
        
    # speeds = DURATION / elapsed_times
    # print('Speeds for all trials:', speeds)

    min_elapsed_time = np.min(elapsed_times)
    speed = int(round(DURATION / min_elapsed_time))
    # print(
    #     f'Fastest trial resampled {DURATION} seconds of audio in '
    #     f'{min_elapsed_time:.1f} seconds, {speed} times faster '
    #     f'than real time.')
    
    return resampling_type, input_rate, output_rate, speed

    
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
    plt.yticks(ys, RESAMPLING_TYPES)
    plt.gca().invert_yaxis()

    # x axis
    plt.xlabel('Speed (times faster than real time)')
    plt.xlim(right=5500)

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
