"""
Constants and functions pertaining to tseep species classifier datasets.
"""


from collections import defaultdict
import math

from tensorflow.data import TFRecordDataset
from tensorflow.io import FixedLenFeature
import tensorflow as tf

import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


_WAVEFORM_EXAMPLE_FEATURES = {
    'waveform': FixedLenFeature((), tf.string),
    'call_start_index': FixedLenFeature((), tf.int64),
    'label': FixedLenFeature((), tf.int64),
    'clip_id': FixedLenFeature((), tf.int64),
}

CLASS_NAMES = '''
ATSP
CCSP_BRSP
CHSP
Double Up
GRSP
LISP
MGWA
SAVS
VESP
WCSP
WIWA
Zeep
'''.strip().split('\n')

CLASS_COUNT = len(CLASS_NAMES)


def create_waveform_dataset_from_tensors(waveforms):
    
    # One might like to just say:
    #
    #     dataset = tf.data.Dataset.from_tensor_slices(waveforms)
    #
    # here instead of using a generator, but that only works if
    # the waveforms all have the same length. Using a generator
    # works even if the waveform lengths differ.
    
    def generator():
        for waveform in waveforms:
            yield _normalize_waveform(waveform)
            
    return tf.data.Dataset.from_generator(generator, tf.float32)
    
    
def create_waveform_dataset_from_tfrecord_files(dir_path):
    
    """
    Creates a dataset of waveforms and associated metadata.
    
    Each dataset example has the form:
    
        (waveform, call_start_index, label, clip_id)
         
    All of the waveforms of the dataset have the same length. Each
    waveform contains one Vesper clip, which contains a nocturnal
    flight call that starts at waveform index `call_start_index`.
    
    The `label` of a dataset example is an integer indicating the
    class of the call.
    
    The `clip_id` of a dataset example is the ID of the clip included
    in the waveform in the Vesper archive to which the clip belongs.
    """
    
    # Use `tf.data.experimental.sample_from_datasets` here.
    
    per_label_datasets = _get_per_label_datasets(dir_path)
    
    dataset = tf.data.experimental.sample_from_datasets(per_label_datasets)
    
    # Parse example protos.
    dataset = dataset.map(
        _parse_example,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    
    return dataset
    
    
def _get_per_label_datasets(dir_path):
    
    file_path_lists = _get_per_label_file_path_lists(dir_path)
    
    return [
        TFRecordDataset(file_paths).repeat()
        for file_paths in file_path_lists]


def _get_per_label_file_path_lists(dir_path):
    
    file_paths = dir_path.glob('*.tfrecords')
    
    file_paths = sorted(file_paths, key=lambda p: p.name)
    
    path_lists_dict = defaultdict(list)
    
    for file_path in file_paths:
        label = _get_label(file_path)
        path_lists_dict[label].append(str(file_path))
        
    path_lists = [
        path_lists_dict[label] for label in sorted(path_lists_dict.keys())]
    
    return path_lists


def _get_label(file_path):
    file_name = file_path.name
    start_index = file_name.find('_') + 1
    end_index = file_name.rfind('_')
    return file_name[start_index:end_index]
    
    
def _parse_example(proto):
    
    example = tf.io.parse_single_example(proto, _WAVEFORM_EXAMPLE_FEATURES)
    
    # Get waveform tensor.
    bytes_ = example['waveform']
    waveform = tf.io.decode_raw(bytes_, out_type=tf.int16, little_endian=True)
    waveform = _normalize_waveform(waveform)
    
    call_start_index = example['call_start_index']
    label = example['label']
    one_hot_label = tf.one_hot(label, CLASS_COUNT)
    clip_id = example['clip_id']
    
    return (waveform, call_start_index, label, one_hot_label, clip_id)
    
    
def _normalize_waveform(waveform):
    
    """
    Normalizes a waveform so it has 32-bit floating point samples in [-1, 1].
    """

    return tf.cast(waveform, tf.float32) / 32768


def create_spectrogram_dataset(dir_path, settings):
    
    """
    Creates a dataset of spectrograms.
    
    Each dataset example has the form:
    
        (spectrogram_slice, call_start_index, label, one_hot_label, clip_id)
    """
    
    dataset = create_waveform_dataset_from_tfrecord_files(dir_path)
    
    processor = _ExampleProcessor(settings)
    
    dataset = dataset.map(
        processor.preprocess_waveform,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    
    dataset = dataset.map(
        processor.compute_spectrogram,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
       
    dataset = dataset.map(
        processor.slice_spectrogram_along_frequency_axis_with_shift,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
       
    dataset = dataset.map(
        processor.normalize_spectrogram_background,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    
    return dataset
     
    
def create_training_dataset(dir_path, settings):
    
    """
    Creates a dataset suitable for training a neural network.
    
    Each dataset example has the form:
    
        (spectrogram_slice, one_hot_label)
        
    All of the spectrogram slices of the dataset have the same shape,
    of the form (spectrum count, bin count, 1). The exact shape depends
    on the values of several `settings` attributes. The spectrogram slices
    are suitable for input into a Keras convolutional neural network.
    
    The `one_hot_label` of a dataset example is a vector whose length
    is the number of example classes, and all of whose elements are
    zero except for one, which has value one.
    """
    
    
    dataset = create_spectrogram_dataset(dir_path, settings)
    
    dataset = dataset.map(
        _diddle_example,
        num_parallel_calls=tf.data.experimental.AUTOTUNE)
    
    return dataset


def _diddle_example(gram, call_start_index, label, one_hot_label, clip_id):
    
    # Reshape gram for input into Keras CNN.
    gram = tf.expand_dims(gram, 2)
        
    # Return only gram and one-hot label, discarding other data.
    return gram, one_hot_label


class _ExampleProcessor:
     
    """
    Dataset example processor.
     
    A dataset example processor prepares dataset examples for input to
    a neural network during training or inference. It performs waveform
    slicing, waveform modifications for dataset augmentation, and
    spectrogram computation.
    """
     
     
    def __init__(self, settings):
         
        self._settings = settings
         
        s = settings
        sample_rate = s.waveform_sample_rate
        
        # Get waveform slice call start index range in samples.
        self._waveform_slice_min_call_start_index = \
            _s2f(s.waveform_slice_min_call_start_time, sample_rate)
        self._waveform_slice_max_call_start_index = \
            _s2f(s.waveform_slice_max_call_start_time, sample_rate)
        
        # Get waveform slice length in samples.
        self._waveform_slice_length = \
            _s2f(s.waveform_slice_duration, sample_rate)
            
        # Get low-level spectrogram settings.
        (self._window_size, self._hop_size, self._dft_size,
         self._freq_start_index, self._freq_end_index) = \
            _get_low_level_spectrogram_settings(s)
        self._window_fn = tf.signal.hann_window
        
        
    def preprocess_waveform(self, waveform, call_start_index, *args):
        
        """
        Preprocesses one input waveform.
        
        Slices and applies data augmentations to the specified waveform
        according to this preprocessor's settings.
        """
        
        s = self._settings
        
        waveform, call_start_index = \
            self._slice_waveform(waveform, call_start_index)
        
        if s.waveform_amplitude_scaling_data_augmentation_enabled:
            waveform = self._scale_waveform_amplitude(waveform)
        
        return (waveform, call_start_index) + tuple(args)
        
        
    def _slice_waveform(self, waveform, call_start_index):
        
        min_index = self._waveform_slice_min_call_start_index
        max_index = self._waveform_slice_max_call_start_index
        
        if min_index == max_index:
            slice_call_start_index = min_index
        else:
            slice_call_start_index = \
                tf.random.uniform((), min_index, max_index, dtype=tf.int64)
            
        slice_start_index = call_start_index - slice_call_start_index
        slice_end_index = slice_start_index + self._waveform_slice_length
        
        waveform_slice = waveform[slice_start_index:slice_end_index]
        
        return waveform_slice, slice_call_start_index
    
    
    def _scale_waveform_amplitude(self, waveform):
        
        max_abs = tf.math.reduce_max(tf.math.abs(waveform))

        if max_abs == 0:
            # waveform samples are all zero
            
            return waveform
        
        else:
            # waveform samples are not all zero
            
            # Find scale factor that would make maximum absolute waveform
            # value one.
            max_factor = _f32(1) / max_abs
            
            # Find scale factor that would reduce RMS waveform value to
            # 1 / 256. Yield 1 if RMS value is already less than 1 / 256.
            sum_squared = tf.math.reduce_sum(waveform * waveform)
            size = tf.cast(tf.size(waveform), tf.float32)
            rms = tf.math.sqrt(sum_squared / size)
            min_factor = tf.math.minimum(_f32(1), _f32(1 / 256) / rms)
            
            # Choose random factor between `min_factor` and `max_factor`,
            # with distribution uniform on log scale.
            max_log = tf.math.log(max_factor)
            min_log = tf.math.log(min_factor)
            log_factor = tf.random.uniform(
                (), min_log, max_log, dtype=tf.float32)
            factor = tf.math.exp(log_factor)
            
            # Scale waveform by chosen factor.
            return factor * waveform
            
            
    def compute_spectrogram(self, waveform, *args):
 
        """Computes the spectrogram of a waveform."""
         
        s = self._settings
         
        # Compute STFT. To use `tf.signal.stft`, we must add a leading
        # unit dimension to the waveform tensor. After the call to
        # `tf.signal.stft` we effectively remove the corresponding
        # dimension of the resulting `stfts` tensor.
        waveforms = tf.expand_dims(waveform, 0)
        stfts = tf.signal.stft(
            waveforms, self._window_size, self._hop_size, self._dft_size,
            self._window_fn)
        stft = stfts[0]
         
        # Get spectrogram, i.e. squared magnitude of STFT.
        gram = tf.math.real(stft * tf.math.conj(stft))
        # gram = tf.abs(stft) ** 2
         
        # Normalize spectrogram values so a full-scale, bin-centered
        # sinusoid has a value of one with a rectangular window.
        # TODO: Consider using a different normalization scheme that
        # yields more consistent values (proportional to the spectral
        # density, with units of watts per hertz) for noise across
        # different sample rates, window sizes, and DFT sizes. This
        # is what we'd like to use for spectrogram display, and it
        # seems that we might as well use it here, too. It isn't
        # necessary to build a working system, but the consistency
        # might be helpful, for example for dataset visualization. 
        normalizing_scale_factor = 1 / (self._window_size / 2) ** 2
        gram *= normalizing_scale_factor
         
        # Take spectrogram log and apply affine transform to put
        # full scale sinusoids at about 100 dB.
        gram = tf.math.log(gram + s.spectrogram_log_epsilon)
        decibel_scale_factor = 10 / math.log(10)
        gram = 100 + decibel_scale_factor * gram
         
        return (gram,) + tuple(args)
     
     
    def slice_spectrogram_along_frequency_axis(self, gram, *args):
        gram = gram[..., self._freq_start_index:self._freq_end_index]
        return (gram,) + tuple(args)
         
         
    def normalize_spectrogram_background(self, gram, *args):
         
        s = self._settings
        rank = s.spectrogram_background_normalization_percentile_rank
         
        if rank is not None:
            ranks = tf.constant([rank])
            percentiles = _get_spectrogram_percentiles(gram, ranks)
            percentiles = tf.reshape(percentiles, (1, tf.size(percentiles)))
            gram = gram - percentiles
             
        return (gram,) + tuple(args)
         
         
    def slice_spectrogram_along_frequency_axis_with_shift(self, gram, *args):
         
        # Get frequency shift in bins.
        max_shift = self._settings.max_spectrogram_frequency_shift
        shift = tf.random.uniform(
            (), -max_shift, max_shift + 1, dtype=tf.int64)
         
        gram = gram[
            ..., self._freq_start_index + shift:self._freq_end_index + shift]
         
        return (gram,) + tuple(args)
         
         
def _s2f(seconds, sample_rate):
    frames = signal_utils.seconds_to_frames(seconds, sample_rate)
    return tf.cast(frames, tf.int64)


def _get_low_level_spectrogram_settings(settings):
     
    s = settings
    fs = s.waveform_sample_rate
    s2f = signal_utils.seconds_to_frames
     
    # spectrogram
    window_size = s2f(s.spectrogram_window_size, fs)
    fraction = s.spectrogram_hop_size / 100
    hop_size = s2f(s.spectrogram_window_size * fraction, fs)
    dft_size = tfa_utils.get_dft_size(window_size)
     
    # frequency slicing
    f2i = tfa_utils.get_dft_bin_num
    freq_start_index = f2i(s.spectrogram_start_freq, fs, dft_size)
    freq_end_index = f2i(s.spectrogram_end_freq, fs, dft_size) + 1
    
    return (window_size, hop_size, dft_size, freq_start_index, freq_end_index)


def _f32(x):
    return tf.cast(x, tf.float32)


_MAX_GRAM_VALUE = 120


def _get_spectrogram_percentiles(gram, percentile_ranks):
    
    # Round gram values to nearest integer.
    gram = tf.cast(tf.round(gram), tf.int32)
    
    # Clip values.
    gram = tf.clip_by_value(gram, 0, _MAX_GRAM_VALUE)
    
    # Transpose gram so first dimension is frequency.
    gram = tf.transpose(gram)
    
    # print('rounded, clipped, and transposed spectrogram:')
    # print(gram)
    
    def accumulate_counts(x):
        length = _MAX_GRAM_VALUE + 1
        counts = tf.math.bincount(x, minlength=length, maxlength=length)
        return tf.cumsum(counts)
    
    cumulative_counts = tf.map_fn(accumulate_counts, gram)
    
    # print()
    # print('cumulative sums of rounded bin value counts:')
    # print(cumulative_counts)

    shape = tf.shape(gram)
    bin_count = shape[0]
    spectrum_count = shape[1]
    percentile_ranks = tf.cast(percentile_ranks, tf.float32)
    thresholds = percentile_ranks / 100. * tf.cast(spectrum_count, tf.float32)
    thresholds = tf.cast(tf.round(thresholds), tf.int32)
    thresholds = tf.reshape(thresholds, (1, len(thresholds)))
    thresholds = tf.tile(thresholds, (bin_count, 1))
    percentiles = tf.searchsorted(cumulative_counts, thresholds)
    
    # print()
    # print('percentiles:')
    # print(percentiles)
    
    return tf.cast(percentiles, tf.float32)


def _get_spectrogram_slice_length(settings):
    s = settings
    slice_duration = s.waveform_slice_duration
    window_size = s.spectrogram_window_size
    hop_size = window_size * s.spectrogram_hop_size / 100
    return 1 + int(round((slice_duration - window_size) / hop_size))
    
    
def _slice_spectrogram(gram, slice_length):
    
    # Get tensor of consecutive spectrogram slices.
    slices = tf.signal.frame(gram, slice_length, frame_step=1, axis=0)
    
    # Add trailing dimension for input into Keras CNN.
    slices = tf.expand_dims(slices, 3)
    
    return slices


def get_spectrogram_slice_shape(settings):
    
    spectrum_count = _get_spectrogram_slice_length(settings)
    
    _, _, _, freq_start_index, freq_end_index = \
        _get_low_level_spectrogram_settings(settings)
    
    bin_count = freq_end_index - freq_start_index
    
    return (spectrum_count, bin_count, 1)
