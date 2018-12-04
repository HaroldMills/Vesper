import functools

import tensorflow as tf

import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


class Preprocessor:
    
    """
    Coarse classifier preprocessor.
    
    A coarse classifier preprocessor prepares classifier input waveforms
    for input to a classifier's neural network during training, evaluation,
    and inference. It performs data augmentation, waveform slicing, and
    spectrogram computation in a TensorFlow graph.
    """
    
    
    MODE_TRAINING = 'Training'
    MODE_EVALUATION = 'Evaluation'
    MODE_INFERENCE = 'Inference'


    @staticmethod
    def get_sliced_spectrogram_size(settings):
        num_spectra, num_bins = \
            Preprocessor.get_sliced_spectrogram_shape(settings)
        return num_spectra * num_bins
    
    
    @staticmethod
    def get_sliced_spectrogram_shape(settings):
        
        (time_start_index, time_end_index, window_size, hop_size, _,
         freq_start_index, freq_end_index) = \
            _get_low_level_preprocessing_settings(
                Preprocessor.MODE_TRAINING, settings)
                    
        num_samples = time_end_index - time_start_index
        num_spectra = tfa_utils.get_num_analysis_records(
            num_samples, window_size, hop_size)
        
        num_bins = freq_end_index - freq_start_index
        
        return (num_spectra, num_bins)
    
    
    def __init__(
            self, preproc_mode, settings, output_feature_name='spectrogram'):
        
        # `preproc_mode` can be `Preprocessor.MODE_TRAINING`,
        # `Preprocessor.MODE_EVALUATION`, or `Preprocessor.MODE_INFERENCE`.
        #
        # When `preproc_mode` is `MODE_TRAINING`, dataset examples are
        # preprocessed according to certain settings that control waveform
        # slicing and data augmentation.
        #
        # When `preproc_mode` is `MODE_EVALUATION`, dataset examples are
        # processed as when it is `MODE_TRAINING`, except that data
        # augmentation can be turned on or off via the
        # `evaluation_data_augmentation_enabled` setting.
        #
        # When `preproc_mode` is `MODE_INFERENCE`, dataset waveforms are
        # not sliced as they are when it is `MODE_TRAINING` or
        # `MODE_EVALUATION`. Instead, the slicing start index is always
        # zero. Data augmentation is also disabled.

        self.settings = settings
        self.output_feature_name = output_feature_name
        
        s = settings
        
        (self.time_start_index, self.time_end_index,
         self.window_size, self.hop_size, self.dft_size,
         self.freq_start_index, self.freq_end_index) = \
            _get_low_level_preprocessing_settings(preproc_mode, s)
         
        self.waveform_length = self.time_end_index - self.time_start_index
                
        self.window_fn = functools.partial(
            tf.contrib.signal.hann_window, periodic=True)
        
        augmentation_enabled = _is_data_augmentation_enabled(preproc_mode, s)
            
        self.random_waveform_time_shifting_enabled = \
            augmentation_enabled and s.random_waveform_time_shifting_enabled
        
        if self.random_waveform_time_shifting_enabled:
            self.max_waveform_time_shift = signal_utils.seconds_to_frames(
                s.max_waveform_time_shift, s.sample_rate)

        
    def preprocess_waveform(self, waveform, label):
        
        """
        Preprocesses one input waveform.
        
        Applies any data augmentation indicated by this preprocessor's
        settings, and extracts the appropriate slice from the resulting
        waveform.
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
        
        return waveform, label
    
    
    def compute_spectrograms(self, waveforms, labels):
        
        """Computes spectrograms for a batch of waveforms."""
        
        s = self.settings
        
        # Set final dimension of waveforms, which comes to us as `None`.
        self._set_waveforms_shape(waveforms)

        # Compute STFTs.
        waveforms = tf.cast(waveforms, tf.float32)
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
            size = Preprocessor.get_sliced_spectrogram_size(s)
            return tf.reshape(grams, (-1, size))

    
def _get_low_level_preprocessing_settings(preproc_mode, settings):
    
    s = settings
    fs = s.sample_rate
    s2f = signal_utils.seconds_to_frames
    
    # time slicing
    if preproc_mode == Preprocessor.MODE_INFERENCE:
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


def _is_data_augmentation_enabled(preproc_mode, settings):
    return \
        preproc_mode == Preprocessor.MODE_TRAINING or \
        preproc_mode == Preprocessor.MODE_EVALUATION and \
        settings.evaluation_data_augmentation_enabled
