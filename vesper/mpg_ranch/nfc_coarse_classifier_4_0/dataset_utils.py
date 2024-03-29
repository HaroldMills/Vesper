"""Constants and functions pertaining to classification datasets."""


import functools
import math

import numpy as np
import tensorflow as tf

import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


# dataset parts
DATASET_PART_TRAINING = 'Training'
DATASET_PART_VALIDATION = 'Validation'
DATASET_PART_TEST = 'Test'

# dataset modes, which influence the preprocessing performed by the dataset
DATASET_MODE_TRAINING = 'Training'
DATASET_MODE_EVALUATION = 'Evaluation'
DATASET_MODE_INFERENCE = 'Inference'

# Target uses, indicating how the trained classifier will be used
# in deployment.
TARGET_USE_OLD_BIRD_COARSE_CLASSIFIER = 'Old Bird Coarse Classifier'
TARGET_USE_DETECTOR = 'Detector'

_WAVEFORM_DATASET_FEATURES = {
    'waveform': tf.FixedLenFeature((), tf.string, default_value=''),
    'label': tf.FixedLenFeature((), tf.int64, default_value=0)
}


def create_spectrogram_dataset_from_waveforms_array(
        waveforms, mode, settings, num_repeats=1, shuffle=False, batch_size=1,
        feature_name='spectrogram'):
    
    dataset = tf.data.Dataset.from_tensor_slices(waveforms)
    
    return _create_spectrogram_dataset(
        dataset, mode, settings, num_repeats, shuffle, batch_size,
        feature_name)
    
    
def create_spectrogram_dataset_from_waveform_files(
        dir_path, mode, settings, num_repeats=1, shuffle=False, batch_size=1,
        feature_name='spectrogram'):
    
    dataset = create_waveform_dataset_from_waveform_files(dir_path)
    
    return _create_spectrogram_dataset(
        dataset, mode, settings, num_repeats, shuffle, batch_size,
        feature_name)

    
def create_waveform_dataset_from_waveform_files(dir_path):
    
    file_path_pattern = str(dir_path / '*.tfrecords')
    
    # Get file paths matching pattern. Sort the paths for consistency.
    file_paths = sorted(tf.gfile.Glob(file_path_pattern))
    
    return tf.data.TFRecordDataset(file_paths).map(_parse_example)


def _parse_example(example_proto):
    
    example = tf.parse_single_example(
        example_proto, _WAVEFORM_DATASET_FEATURES)
    
    bytes_ = example['waveform']
    waveform = tf.decode_raw(bytes_, out_type=tf.int16, little_endian=True)
    
    label = example['label']
    
    return waveform, label


def _create_spectrogram_dataset(
        waveform_dataset, mode, settings, num_repeats=1, shuffle=False,
        batch_size=1, feature_name='spectrogram'):
    
    preprocessor = _Preprocessor(mode, settings, feature_name)
    
    dataset = waveform_dataset
    
    if num_repeats is None:
        dataset = dataset.repeat()
    elif num_repeats != 1:
        dataset = dataset.repeat(num_repeats)
    
    dataset = dataset.map(
        preprocessor.preprocess_waveform,
        num_parallel_calls=settings.num_dataset_parallel_calls)
    
    if shuffle:
        dataset = dataset.shuffle(10 * batch_size)
        
    if batch_size != 1:
        dataset = dataset.batch(batch_size)
    
    dataset = dataset.map(
        preprocessor.compute_spectrograms,
        num_parallel_calls=settings.num_dataset_parallel_calls)
    
    return dataset


class _Preprocessor:
    
    """
    Dataset example preprocessor.
    
    A dataset example preprocessor prepares dataset examples for input to
    a classifier's neural network during training, evaluation, and inference.
    It performs waveform shifting, scaling, and slicing, and spectrogram
    computation in a TensorFlow graph.
    """
    
    
    def __init__(self, mode, settings, output_feature_name='spectrogram'):
        
        # `mode` can be `DATASET_MODE_TRAINING`, `DATASET_MODE_EVALUATION`,
        # or `DATASET_MODE_INFERENCE`.
        #
        # When `mode` is `DATASET_MODE_TRAINING` or
        # `DATASET_MODE_EVALUATION, dataset examples are preprocessed
        # according to certain settings that control waveform modification
        # and slicing.
        #
        # When `mode` is `DATASET_MODE_INFERENCE`, waveform modification
        # is disabled and the slicing start index is always zero.

        self.settings = settings
        self.output_feature_name = output_feature_name
        
        s = settings
        
        (self.time_start_index, self.time_end_index,
         self.window_size, self.hop_size, self.dft_size,
         self.freq_start_index, self.freq_end_index) = \
            _get_low_level_preprocessing_settings(mode, s)
         
        self.waveform_length = self.time_end_index - self.time_start_index
                
        self.window_fn = functools.partial(
            tf.contrib.signal.hann_window, periodic=True)
        
        # Note that we perform random waveform time shifting in the
        # evaluation dataset mode for a classifier that will be deployed
        # in a detector. The distribution of event onset times within
        # clips created by the Old Bird detectors (the current source of
        # our training data) is less uniform than the more or less flat
        # distribution that a classifier sees in the recording segments
        # presented to it when it is deployed in a detector. Random waveform
        # time shifting flattens and widens the onset time distribution in
        # the dataset, making it more like what it will see in deployment.
        self.random_waveform_time_shifting_enabled = \
            s.random_waveform_time_shifting_enabled and (
                mode == DATASET_MODE_TRAINING or (
                    mode == DATASET_MODE_EVALUATION and
                    s.target_use == TARGET_USE_DETECTOR))
                
        if self.random_waveform_time_shifting_enabled:
            self.max_waveform_time_shift = signal_utils.seconds_to_frames(
                s.max_waveform_time_shift, s.waveform_sample_rate)

        # We perform random waveform amplitude scaling during training
        # in order to make the distribution of input amplitudes wider
        # and more uniform, with the intent of making the classifier
        # less sensitive to variation in input amplitude. We perform
        # the same scaling during evaluation in order to gauge the
        # classifier's performance on a similar input amplitude
        # distribution. If in the future we perform some sort of
        # amplitude normalization (e.g. PCEN or normalization based
        # on order statistical background noise power estimates), the
        # random scaling may no longer be needed.
        self.random_waveform_amplitude_scaling_enabled = \
            s.random_waveform_amplitude_scaling_enabled and (
                mode == DATASET_MODE_TRAINING or
                mode == DATASET_MODE_EVALUATION)
                

    def preprocess_waveform(self, waveform, label=None):
        
        """
        Preprocesses one input waveform.
        
        Applies any waveform modifications indicated by this
        preprocessor's settings, and extracts the appropriate slice
        from the resulting waveform.
        """
        
        # Get time shifting offset.
        if self.random_waveform_time_shifting_enabled:
            n = self.max_waveform_time_shift
            offset = tf.random.uniform((), -n, n, dtype=tf.int32)
        else:
            offset = 0
            
        # Slice waveform.
        start_index = self.time_start_index + offset
        end_index = self.time_end_index + offset
        waveform = waveform[start_index:end_index]
        
        # Cast waveform to float32 for subsequent processing.
        waveform = tf.cast(waveform, tf.float32)
        
        if self.random_waveform_amplitude_scaling_enabled:
            waveform = self._scale_waveform_amplitude(waveform)
            
        if label is None:
            return waveform
        else:
            return waveform, label
    
    
    def _scale_waveform_amplitude(self, waveform):
          
        max_abs = tf.math.reduce_max(tf.math.abs(waveform))

        def do_not_scale():
            return waveform
        
        def scale():
            
            # Find scale factor that would make maximum absolute waveform
            # value 32767.
            max_factor = _f32(32767) / max_abs
              
            # Find scale factor that would reduce RMS waveform value to
            # 256, or 1 if RMS value is already less than 256.
            sum_squared = tf.math.reduce_sum(waveform * waveform)
            size = tf.cast(tf.size(waveform), tf.float32)
            rms = tf.math.sqrt(sum_squared / size)
            min_factor = tf.math.minimum(_f32(1), _f32(256) / rms)
              
            # Choose random factor between `min_factor` and `max_factor`,
            # with distribution uniform on log scale.
            max_log = tf.math.log(max_factor)
            min_log = tf.math.log(min_factor)
            log_factor = tf.random.uniform(
                (), min_log, max_log, dtype=tf.float32)
            factor = tf.math.exp(log_factor)
              
            # Scale waveform by chosen factor.
            return factor * waveform
            
        # Scale waveform if and only if it isn't zero (attempting to
        # scale when the waveform is zero results in divisions by zero).
        return tf.cond(tf.equal(max_abs, 0), do_not_scale, scale)
    

    def compute_spectrograms(self, waveforms, labels=None):
        
        """Computes spectrograms for a batch of waveforms."""
        
        s = self.settings
        
        # Set final dimension of waveforms, which comes to us as `None`.
        self._set_waveforms_shape(waveforms)

        # Compute STFTs.
        stfts = tf.contrib.signal.stft(
            waveforms, self.window_size, self.hop_size,
            fft_length=self.dft_size, window_fn=self.window_fn)
        
        # Slice STFTs along frequency axis.
        stfts = stfts[..., self.freq_start_index:self.freq_end_index]
        
        # Get STFT magnitudes squared, i.e. squared spectrograms.
        grams = tf.real(stfts * tf.conj(stfts))
        # gram = tf.abs(stft) ** 2
        
        # Take natural log of squared spectrograms. Adding an epsilon
        # avoids log-of-zero errors.
        grams = tf.log(grams + s.spectrogram_log_epsilon)
        
        # Clip spectrograms if indicated.
        if s.spectrogram_clipping_enabled:
            grams = tf.clip_by_value(
                grams, s.spectrogram_clipping_min, s.spectrogram_clipping_max)
            
        # Normalize spectrograms if indicated.
        if s.spectrogram_normalization_enabled:
            grams = \
                s.spectrogram_normalization_scale_factor * grams + \
                s.spectrogram_normalization_offset
        
        # Reshape spectrograms for input into Keras neural network.
        grams = self._reshape_grams(grams)
        
        # Create features dictionary.
        features = {self.output_feature_name: grams}
        
        if labels is None:
            
            return features
        
        else:
            # have labels
        
            # Reshape labels into a single 2D column.
            labels = tf.reshape(labels, (-1, 1))
            
            return features, labels
    
    
    def _set_waveforms_shape(self, waveforms):
        
        """
        Sets the final dimension of a batch of waveforms.
        
        When we receive a batch of waveforms its final dimension is
        `None`, even though we know that the dimension is the sliced
        waveform length. We set the dimension since if we don't and
        the model includes at least one convolutional layer, then
        the `Classifier.train` method raises an exception.
        """
        
        dims = list(waveforms.shape.dims)
        dims[-1] = tf.Dimension(self.waveform_length)
        shape = tf.TensorShape(dims)
        waveforms.set_shape(shape)
        
        
    def _reshape_grams(self, grams):
        
        """
        Reshapes a batch of spectrograms for input to a Keras neural network.
        
        The batch must be reshaped differently depending on whether the
        network's input layer is convolutional or dense.
        """
        
        s = self.settings
        
        if len(s.convolutional_layer_sizes) != 0:
            # model is CNN
            
            # Add channel dimension for Keras `Conv2D` layer compatibility.
            return tf.expand_dims(grams, 3)
            
        else:
            # model is DNN
            
            # Flatten spectrograms for Keras `Dense` layer compatibility.
            size = get_sliced_spectrogram_size(s)
            return tf.reshape(grams, (-1, size))

    
def _get_low_level_preprocessing_settings(mode, settings):
    
    s = settings
    fs = s.waveform_sample_rate
    s2f = signal_utils.seconds_to_frames
    
    # time slicing
    if mode == DATASET_MODE_INFERENCE:
        time_start_index = 0
    else:
        time_start_index = s2f(s.waveform_start_time, fs)
    length = s2f(s.waveform_duration, fs)
    time_end_index = time_start_index + length
    
    # spectrogram
    window_size = s2f(s.spectrogram_window_size, fs)
    fraction = s.spectrogram_hop_size / 100
    hop_size = s2f(s.spectrogram_window_size * fraction, fs)
    dft_size = tfa_utils.get_dft_size(window_size)
    
    # frequency slicing
    f2i = tfa_utils.get_dft_bin_num
    freq_start_index = f2i(s.spectrogram_start_freq, fs, dft_size)
    freq_end_index = f2i(s.spectrogram_end_freq, fs, dft_size) + 1
    
    return (
        time_start_index, time_end_index, window_size, hop_size, dft_size,
        freq_start_index, freq_end_index)


def get_sliced_spectrogram_size(settings):
    num_spectra, num_bins = get_sliced_spectrogram_shape(settings)
    return num_spectra * num_bins


def get_sliced_spectrogram_shape(settings):
    
    (time_start_index, time_end_index, window_size, hop_size, _,
     freq_start_index, freq_end_index) = \
        _get_low_level_preprocessing_settings(
            DATASET_MODE_TRAINING, settings)
                
    num_samples = time_end_index - time_start_index
    num_spectra = tfa_utils.get_num_analysis_records(
        num_samples, window_size, hop_size)
    
    num_bins = freq_end_index - freq_start_index
    
    return (num_spectra, num_bins)
    
    
def _f32(x):
    return tf.cast(x, tf.float32)


def show_dataset(dataset, num_batches):

    print('output_types', dataset.output_types)
    print('output_shapes', dataset.output_shapes)
    
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        num_values = 0
        values_sum = 0
        squares_sum = 0
        
        for i in range(num_batches):
                
            features, labels = session.run(next_batch)
            feature_name, values = list(features.items())[0]
                
            values_class = values.__class__.__name__
            labels_class = labels.__class__.__name__
            
            num_values += values.size
            values_sum += values.sum()
            squares_sum += (values ** 2).sum()
            
            mean = values_sum / num_values
            std_dev = math.sqrt(squares_sum / num_values - mean ** 2)
            
            print(
                'Batch {} of {}: {} {} {} {} {}, labels {} {}'.format(
                    i + 1, num_batches, feature_name, values_class,
                    values.shape, mean, std_dev, labels_class, labels.shape))
                    

def _main():
    _test_random_time_shifting()
    
    
def _test_random_time_shifting():
    
    """
    Tests random time shifting waveform modification.
    
    Random time shifting is used by the `WaveformPreprocessor` class to
    distribute event onset times more evenly during classifier training.
    """
    
    class ShiftingSlicer:
        
        def __init__(self):
            self.max_shift = 2
            self.length = 3
            
        def __call__(self, x):
            n = self.max_shift
            i = tf.random.uniform((), -n, n, dtype=tf.int32)
            return x[n + i:n + self.length + i]
    
    # Create dataset as NumPy array.
    m = 10
    n = 6
    x = 100 * np.arange(m).reshape((m, 1)) + np.arange(n).reshape((1, n))

    # Create TensorFlow dataset.
    slicer = ShiftingSlicer()
    dataset = tf.data.Dataset.from_tensor_slices(x).repeat(2).map(slicer)
    
    # Show dataset.
    iterator = dataset.make_one_shot_iterator()
    x = iterator.get_next()
     
    with tf.Session() as session:
        
        while True:
            
            try:
                x_ = session.run(x)
                print(x_)
                
            except tf.errors.OutOfRangeError:
                break    
    

if __name__ == '__main__':
    _main()
