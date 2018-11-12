"""
Trains a Vesper coarse clip classifier.

A coarse clip classifier is a binary classifier that tries to determine
whether or not a clip contains a nocturnal flight call.
"""


from pathlib import Path
import functools
import math
import time

import numpy as np
import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.time_frequency_analysis_utils as tfa_utils


DATA_DIR_PATH_FORMAT = (
    '/Users/harold/Desktop/NFC/Data/Vesper ML Datasets/'
    'Coarse Classification/{}/{}')
DATA_FILE_NAME_FORMAT = '{}_{}_{}.tfrecords'

EXAMPLE_FEATURES = {
    'waveform': tf.FixedLenFeature((), tf.string, default_value=''),
    'label': tf.FixedLenFeature((), tf.int64, default_value=0)
}

SETTINGS = {
     
    'Tseep': Settings(
        
        clip_type='Tseep',
        
        dataset_name='Tseep 100K',
        
        sample_rate=24000,
        
        # waveform slicing settings
        waveform_start_time=.080,
        waveform_duration=.150,
        
        # spectrogram settings
        spectrogram_window_size=.005,
        spectrogram_hop_size=.5,
        spectrogram_log_epsilon=1e-10,
        
        # spectrogram frequency axis slicing settings
        spectrogram_start_freq=4000,
        spectrogram_end_freq=10000,
        
        # number of parallel calls for input and spectrogram computation
        num_preprocessing_parallel_calls=4,
        
        # spectrogram clipping pretraining settings
        spectrogram_clipping_pretraining_enabled=True,
        pretraining_num_examples=20000,
        pretraining_batch_size=1000,
        pretraining_histogram_min=-25,
        pretraining_histogram_max=50,
        pretraining_histogram_num_bins=750,
        pretraining_clipped_values_fraction=.001,
        pretraining_value_distribution_plotting_enabled=False,
        
        # spectrogram normalization pretraining settings
        spectrogram_normalization_pretraining_enabled=True,
        
        # spectrogram clipping settings
        spectrogram_clipping_enabled=True,
        spectrogram_clipping_min=None,
        spectrogram_clipping_max=None,
        
        # spectrogram normalization settings
        spectrogram_normalization_enabled=True,
        spectrogram_normalization_scale_factor=None,
        spectrogram_normalization_offset=None,
        
        batch_size=64,
        
    )
    
}


def main():
    
    settings = SETTINGS['Tseep']
    
    # show_spectrogram_dataset(settings)
    
    train_classifier(settings)
    
    
def show_spectrogram_dataset(settings):
    
    total_num_examples = 2 ** 13
    batch_size = 2 ** 6
    
    dataset = create_spectrogram_dataset(settings, batch_size)
    
    num_batches = int(round(total_num_examples / batch_size))
    show_dataset(dataset, num_batches)


def create_spectrogram_dataset(
        settings, dataset_type, batch_size=None,
        spectrogram_clipping_enabled=None,
        spectrogram_normalization_enabled=None):
    
    dataset = create_base_dataset(settings.dataset_name, dataset_type)
    
    batch_size = get_batch_size(settings, batch_size)
    if batch_size != 1:
        dataset = dataset.batch(batch_size)
    
    if spectrogram_clipping_enabled is not None:
        settings = Settings(
            settings,
            spectrogram_clipping_enabled=spectrogram_clipping_enabled)
        
    if spectrogram_normalization_enabled is not None:
        enabled = spectrogram_normalization_enabled  # to shorten line below
        settings = Settings(
            settings, spectrogram_normalization_enabled=enabled)

    preprocessor = Preprocessor(settings)
    
    dataset = dataset.map(
        preprocessor,
        num_parallel_calls=settings.num_preprocessing_parallel_calls)
    
    return dataset
    

def create_base_dataset(dataset_name, dataset_type):
    
    file_path_pattern = create_data_file_path(dataset_name, dataset_type, '*')
    
    # Get file paths matching pattern. Sort the paths for consistency.
    file_paths = sorted(tf.gfile.Glob(file_path_pattern))
    
    return tf.data.TFRecordDataset(file_paths).map(parse_example)
            
        
def create_data_file_path(dataset_name, dataset_type, file_num):
    dir_path = DATA_DIR_PATH_FORMAT.format(dataset_name, dataset_type)
    file_name = DATA_FILE_NAME_FORMAT.format(
        dataset_name, dataset_type, file_num)
    return str(Path(dir_path) / file_name)
    

def parse_example(example_proto):
    
    example = tf.parse_single_example(example_proto, EXAMPLE_FEATURES)
    
    bytes_ = example['waveform']
    waveform = tf.decode_raw(bytes_, out_type=tf.int16, little_endian=True)
    
    label = example['label']
    
    return waveform, label


def get_batch_size(settings, batch_size):
    
    if batch_size is None:
        
        if settings.batch_size is not None:
            batch_size = settings.batch_size
        else:
            batch_size = 1
            
        batch_size = settings.batch_size
        
    return batch_size
        

def show_dataset(dataset, num_batches):

    print('output types', dataset.output_types)
    print('output_shapes', dataset.output_shapes)
    
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        start_time = time.time()
        
        num_values = 0
        values_sum = 0
        squares_sum = 0
        
        for i in range(num_batches):
                
            x, labels = session.run(next_batch)
                
            x_class = x.__class__.__name__
            labels_class = labels.__class__.__name__
            
            num_values += x.size
            values_sum += x.sum()
            squares_sum += (x ** 2).sum()
            
            mean = values_sum / num_values
            sigma = math.sqrt(squares_sum / num_values - mean ** 2)
            
            print(
                'Batch {} of {}: x {} {} {} {}, labels {} {}'.format(
                    i + 1, num_batches, x_class, x.shape, mean, sigma,
                    labels_class, labels.shape))
            
        print('Iteration took {} seconds.'.format(time.time() - start_time))
                    

def train_classifier(settings):
    
    if settings.spectrogram_clipping_pretraining_enabled:
        compute_spectrogram_clipping_settings(settings)
        
    if settings.spectrogram_normalization_pretraining_enabled:
        compute_spectrogram_normalization_settings(settings)
        
    train_dataset = create_spectrogram_dataset(settings, 'Training')
    
    show_dataset(train_dataset, 20)
    
    
def compute_spectrogram_clipping_settings(settings):
    
    s = settings
    
    num_examples = s.pretraining_num_examples
    batch_size = s.pretraining_batch_size
    num_batches = int(round(num_examples / batch_size))
    
    hist_min = s.pretraining_histogram_min
    hist_max = s.pretraining_histogram_max
    num_bins = s.pretraining_histogram_num_bins
    bin_size = (hist_max - hist_min) / num_bins
    log_epsilon = math.log(settings.spectrogram_log_epsilon)
    
    dataset = create_spectrogram_dataset(
        settings, 'Training', batch_size, spectrogram_clipping_enabled=False,
        spectrogram_normalization_enabled=False)
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        print(
            'Computing spectrogram clipping range from {} examples...'.format(
                num_batches * batch_size))
        
        start_time = time.time()
        
        histogram = np.zeros(num_bins)
        
        for _ in range(num_batches):
                
            grams, _ = session.run(next_batch)
            
            h, edges = np.histogram(grams, num_bins, (hist_min, hist_max))
            histogram += h
            
            # If one of the histogram bins includes the log power to which
            # zero spectrogram values are mapped, zero that bin to ensure that
            # it doesn't interfere with computing a good minimum power value.
            if hist_min <= log_epsilon and log_epsilon <= hist_max:
                bin_num = int(math.floor((log_epsilon - hist_min) / bin_size))
                # print('Zeroing histogram bin {}.'.format(bin_num))
                histogram[bin_num] = 0
           
            # Compute clipping powers.
            cumsum = histogram.cumsum() / histogram.sum()
            threshold = s.pretraining_clipped_values_fraction / 2
            min_index = np.searchsorted(cumsum, threshold, side='right')
            max_index = np.searchsorted(cumsum, 1 - threshold) + 1
            min_value = edges[min_index]
            max_value = edges[max_index]
                
            # print(
            #     'Batch {} of {}: ({}, {})'.format(
            #         i + 1, num_batches, min_value, max_value))
            
        end_time = time.time()
        delta_time = end_time - start_time
        print(
            'Computed spectrogram clipping range in {} seconds.'.format(
                delta_time))
        print('Clipping range is ({}, {}).'.format(min_value, max_value))

    # Plot spectrogram value distribution and clipping limits.
    if s.pretraining_value_distribution_plotting_enabled:
        import matplotlib.pyplot as plt
        distribution = histogram / histogram.sum()
        plt.figure(1)
        plt.plot(edges[:-1], distribution)
        plt.axvline(min_value, color='r')
        plt.axvline(max_value, color='r')
        plt.xlim((edges[0], edges[-1]))
        plt.title('Distribution of Spectrogram Values')
        plt.xlabel('Log Power')
        plt.show()

    s.spectrogram_clipping_min = min_value
    s.spectrogram_clipping_max = max_value
    
    
def compute_spectrogram_normalization_settings(settings):
    
    s = settings
    
    num_examples = s.pretraining_num_examples
    batch_size = s.pretraining_batch_size
    num_batches = int(round(num_examples / batch_size))
    
    dataset = create_spectrogram_dataset(
        settings, 'Training', batch_size, spectrogram_clipping_enabled=True,
        spectrogram_normalization_enabled=False)
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        print((
            'Computing spectrogram normalization settings from {} '
            'examples...').format(num_batches * batch_size))
        
        start_time = time.time()
        
        num_values = 0
        values_sum = 0
        squares_sum = 0
        
        for _ in range(num_batches):
                
            grams, _ = session.run(next_batch)
            
            num_values += grams.size
            values_sum += grams.sum()
            squares_sum += (grams ** 2).sum()
            
            mean = values_sum / num_values
            sigma = math.sqrt(squares_sum / num_values - mean ** 2)
            
            # print(
            #     'Batch {} of {}: ({}, {})'.format(
            #         i + 1, num_batches, mean, sigma))
            
        end_time = time.time()
        delta_time = end_time - start_time
        print((
            'Computed spectrogram normalization settings in {} '
            'seconds.').format(delta_time))
        print(
            'Normalization mean and standard deviation are ({}, {}).'.format(
                mean, sigma))
        
    s.spectrogram_normalization_scale_factor = 1 / sigma
    s.spectrogram_normalization_offset = -mean / sigma

    
class Preprocessor:
    
    
    def __init__(self, settings):
        
        self.settings = settings
        
        s = settings
        fs = s.sample_rate
        
        # time slicing
        self.time_start_index = int(round(s.waveform_start_time * fs))
        end_time = s.waveform_start_time + s.waveform_duration
        self.time_end_index = int(round(end_time * fs))
        
        # spectrogram
        self.window_size = int(round(s.spectrogram_window_size * fs))
        self.window_fn = functools.partial(
            tf.contrib.signal.hann_window, periodic=True)
        self.hop_size = int(round(self.window_size * s.spectrogram_hop_size))
        self.dft_size = tfa_utils.get_dft_size(self.window_size)
        
        # frequency slicing
        bin_size = fs / self.dft_size
        self.freq_start_index = \
            int(math.floor(s.spectrogram_start_freq / bin_size))
        self.freq_end_index = \
            int(math.ceil(s.spectrogram_end_freq / bin_size))
        
        
    def __call__(self, waveforms, labels):
        
        """Computes spectrograms for a batch of waveforms."""
        
        s = self.settings
        
        # Slice waveforms.
        waveforms = waveforms[..., self.time_start_index:self.time_end_index]
        
        # Compute STFTs.
        waveforms = tf.cast(waveforms, tf.float32)
        stfts = tf.contrib.signal.stft(
            waveforms, self.window_size, self.hop_size,
            fft_length=self.dft_size, window_fn=self.window_fn)
        
        # Slice STFTs along frequency axis.
        stfts = stfts[..., self.freq_start_index:self.freq_end_index + 1]
        
        # Get STFT magnitudes squared, i.e. squared spectrograms.
        grams = tf.real(stfts * tf.conj(stfts))
        # gram = tf.abs(stft) ** 2
        
        # Take natural log of squared spectrograms. Adding an epsilon
        # avoids log-of-zero errors.
        grams = tf.log(grams + s.spectrogram_log_epsilon)
        
        # Clip spectrograms if indicated.
        if self.settings.spectrogram_clipping_enabled:
            grams = tf.clip_by_value(
                grams, s.spectrogram_clipping_min, s.spectrogram_clipping_max)
            
        # Normalize spectrograms if indicated.
        if self.settings.spectrogram_normalization_enabled:
            grams = \
                s.spectrogram_normalization_scale_factor * grams + \
                s.spectrogram_normalization_offset
        
        return grams, labels
    
        
class WaveformSlicer:
    
    
    def __init__(self, settings):
        s = settings
        fs = s.sample_rate
        self.start_index = int(round(s.waveform_start_time * fs))
        end_time = s.waveform_start_time + s.waveform_duration
        self.end_index = int(round(end_time * fs))
        
        
    def __call__(self, waveforms, labels):
        sliced_waveforms = waveforms[..., self.start_index:self.end_index]
        return sliced_waveforms, labels
    
    
if __name__ == '__main__':
    main()
