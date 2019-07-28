"""
Trains a Vesper coarse clip classifier.

A coarse clip classifier is a binary classifier that tries to determine
whether or not a clip contains a nocturnal flight call.
"""


from pathlib import Path
import bisect
import math
import os
import shutil
import time

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

from vesper.mpg_ranch.nfc_coarse_classifier_4_0.dataset_utils import (
    DATASET_MODE_EVALUATION, DATASET_MODE_TRAINING, DATASET_PART_TRAINING,
    DATASET_PART_VALIDATION)
from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_4_0.classifier_utils as \
    classifier_utils
import vesper.mpg_ranch.nfc_coarse_classifier_4_0.dataset_utils as \
    dataset_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.script_utils as script_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Tune hyperparameters.
# TODO: Evaluate on only initial portion of training data.
# TODO: Save SavedModels and performance models and stats periodically.


CLASSIFIER_NAME = 'Thrush 600K'

CALL_TYPE = CLASSIFIER_NAME.split()[0]

BASE_DIR_PATH = Path('/Users/harold/Desktop')

ML_DIR_PATH = \
    BASE_DIR_PATH / 'NFC' / 'Data' / 'Vesper ML' / \
    'MPG Ranch Coarse Classifier 4.0'
DATASETS_DIR_PATH = ML_DIR_PATH / 'Datasets' / CALL_TYPE
MODELS_DIR_PATH = ML_DIR_PATH / 'Models' / CALL_TYPE
SAVED_MODELS_DIR_NAME = 'Saved Models'

RESULTS_DIR_PATH = BASE_DIR_PATH / 'ML Results'
PR_PLOT_FILE_NAME_FORMAT = '{} PR.pdf'
ROC_PLOT_FILE_NAME_FORMAT = '{} ROC.pdf'
PR_CSV_FILE_NAME_FORMAT = '{} PR.csv'

PR_CSV_FILE_HEADER = (
    'Threshold,'
    'Training Recall,'
    'Training Precision,'
    'Validation Recall,'
    'Validation Precision\n')

PR_CSV_FILE_ROW_FORMAT = '{:.2f},{:.3f},{:.3f},{:.3f},{:.3f}\n'

BASE_TSEEP_SETTINGS = Settings(
    
    target_use=dataset_utils.TARGET_USE_DETECTOR,
    
    dataset_name='Tseep 850K',
    
    waveform_sample_rate=24000,
    
    # The onsets of detected events (whether calls or non-calls) in clips
    # created by Vesper's Old Bird Tseep Detector Redux 1.1 occur within
    # a window that starts roughly 90 ms into the clips of our datasets
    # and is about 50 ms wide. The onsets are not uniformly distributed
    # within this window: the location of an onset in the window depends
    # on the strength and bandwidth of the event, and more onsets occur
    # later in the window than earlier. In the future, I hope to shrink
    # the window in our datasets, and make the distribution of onsets
    # within the window more uniform.
    #
    # Random waveform time shifting is a waveform modification method
    # that distributes training clip event onset times more evenly. When
    # random waveform time shifting is enabled, each dataset waveform is
    # shifted in time by an amount drawn from the uniform distribution
    # over [-max_waveform_time_shift, max_waveform_time_shift] before the
    # waveform is sliced. The distribution of onsets after shifting is the
    # distribution before shifting convolved with the shift distribution.
    # Note that this widens the window within which onsets can occur by
    # max_waveform_time_shift seconds on each end.
    
    # location of event onset window in training dataset waveforms
    event_onset_window_start_time=.090,
    event_onset_window_duration=.050,
    
    # random waveform time shifting waveform modification settings
    random_waveform_time_shifting_enabled=True,
    max_waveform_time_shift=.025,
    
    # Random waveform amplitude scaling is a waveform modification method
    # that distributes waveform amplitudes more evenly. When random
    # waveform amplitude scaling is enabled, the RMS amplitude of a
    # waveform is modified to a value whose logarithm is drawn from the
    # uniform distribution over a certain range.
    random_waveform_amplitude_scaling_enabled=True,
    
    # waveform settings
    waveform_initial_padding=.050,
    waveform_duration=.190,
    
    # Difference between dataset waveform start time and start time of
    # corresponding detected clip. We use this during inference to help
    # figure out which portion of a clip should be input to the
    # classifier.
    inference_waveform_start_time_offset=0,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=50,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=4000,
    spectrogram_end_freq=10000,
    
    # number of parallel calls for dataset example preprocessing
    num_dataset_parallel_calls=4,
    
    # spectrogram clipping settings
    spectrogram_clipping_enabled=True,
    spectrogram_clipping_min=None,
    spectrogram_clipping_max=None,
    
    # spectrogram normalization settings
    spectrogram_normalization_enabled=True,
    spectrogram_normalization_scale_factor=None,
    spectrogram_normalization_offset=None,
    
    # spectrogram clipping and normalization pretraining settings
    spectrogram_clipping_pretraining_enabled=True,
    spectrogram_normalization_pretraining_enabled=True,
    pretraining_num_examples=20000,
    pretraining_batch_size=100,
    pretraining_histogram_min=-25,
    pretraining_histogram_max=50,
    pretraining_histogram_num_bins=750,
    pretraining_clipped_values_fraction=.001,
    pretraining_value_distribution_plotting_enabled=False,
    
    # neural network settings
    convolutional_layer_sizes=[16, 32],
    dense_layer_sizes=[16],
    batch_normalization_enabled=True,
    l2_regularization_enabled=False,
    l2_regularization_beta=.002,
    
    # neural network training settings
    training_batch_size=128,
    num_training_steps=50000,
    warm_start_enabled=False,
    
    # evaluation plot settings
    precision_recall_plot_lower_axis_limit=.80,
    precision_recall_plot_major_tick_interval=.05,
    precision_recall_plot_minor_tick_interval=.01,
    
    # classifier performance settings
    min_classifier_recall=.98
    
)


BASE_THRUSH_SETTINGS = Settings(
    
    target_use=dataset_utils.TARGET_USE_DETECTOR,
    
    dataset_name='Thrush 600K',
    
    waveform_sample_rate=24000,
    
    # The onsets of detected events (whether calls or non-calls) in clips
    # created by Vesper's Old Bird Thrush Detector Redux 1.1 occur within
    # a window that starts roughly 210 ms into the clips of our datasets
    # and is about 80 ms wide. The onsets are not uniformly distributed
    # within this window: the location of an onset in the window depends
    # on the strength and bandwidth of the event, and more onsets occur
    # later in the window than earlier. In the future, I hope to shrink
    # the window in our datasets, and make the distribution of onsets
    # within the window more uniform.
    #
    # Random waveform time shifting is a waveform modification method
    # that distributes training clip event onset times more evenly. When
    # random waveform time shifting is enabled, each dataset waveform is
    # shifted in time by an amount drawn from the uniform distribution
    # over [-max_waveform_time_shift, max_waveform_time_shift] before the
    # waveform is sliced. The distribution of onsets after shifting is the
    # distribution before shifting convolved with the shift distribution.
    # Note that this widens the window within which onsets can occur by
    # max_waveform_time_shift seconds on each end.
    
    # location of event onset window in training dataset waveforms
    event_onset_window_start_time=.110,
    event_onset_window_duration=.080,
    
    # random waveform time shifting waveform modification settings
    random_waveform_time_shifting_enabled=True,
    max_waveform_time_shift=.025,
    
    # Random waveform amplitude scaling is a waveform modification method
    # that distributes waveform amplitudes more evenly. When random
    # waveform amplitude scaling is enabled, the RMS amplitude of a
    # waveform is modified to a value whose logarithm is drawn from the
    # uniform distribution over a certain range.
    random_waveform_amplitude_scaling_enabled=True,
    
    # waveform settings
    waveform_initial_padding=.030,
    waveform_duration=.250,
    
    # Difference between dataset waveform start time and start time of
    # corresponding detected clip. We use this during inference to help
    # figure out which portion of a clip should be input to the
    # classifier.
    inference_waveform_start_time_offset=.050,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=50,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=2000,
    spectrogram_end_freq=5000,
    
    # number of parallel calls for dataset example preprocessing
    num_dataset_parallel_calls=4,
    
    # spectrogram clipping settings
    spectrogram_clipping_enabled=True,
    spectrogram_clipping_min=None,
    spectrogram_clipping_max=None,
    
    # spectrogram normalization settings
    spectrogram_normalization_enabled=True,
    spectrogram_normalization_scale_factor=None,
    spectrogram_normalization_offset=None,
    
    # spectrogram clipping and normalization pretraining settings
    spectrogram_clipping_pretraining_enabled=True,
    spectrogram_normalization_pretraining_enabled=True,
    pretraining_num_examples=20000,
    pretraining_batch_size=100,
    pretraining_histogram_min=-25,
    pretraining_histogram_max=50,
    pretraining_histogram_num_bins=750,
    pretraining_clipped_values_fraction=.001,
    pretraining_value_distribution_plotting_enabled=False,
    
    # neural network settings
    convolutional_layer_sizes=[16, 32],
    dense_layer_sizes=[16],
    batch_normalization_enabled=True,
    l2_regularization_enabled=False,
    l2_regularization_beta=.002,
    
    # neural network training settings
    training_batch_size=128,
    num_training_steps=20000,
    warm_start_enabled=False,
    
    # evaluation plot settings
    precision_recall_plot_lower_axis_limit=.80,
    precision_recall_plot_major_tick_interval=.05,
    precision_recall_plot_minor_tick_interval=.01,
    
    # classifier performance settings
    min_classifier_recall=.97
    
)


SETTINGS = {
    
    'Tseep Quick': Settings(BASE_TSEEP_SETTINGS, Settings(
        dataset_name='Tseep 100K',
        pretraining_num_examples=1000,
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16],
        num_training_steps=1000
    )),    
    
    'Tseep Logistic Regression': Settings(BASE_TSEEP_SETTINGS, Settings(
        dataset_name='Tseep 100K',
        convolutional_layer_sizes=[],
        dense_layer_sizes=[],
        num_training_steps=5000
    )),
    
    'Tseep Baseline': Settings(BASE_TSEEP_SETTINGS, Settings(
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16]
    )),
    
    'Tseep 100K': Settings(BASE_TSEEP_SETTINGS, Settings(
        
        dataset_name='Tseep 100K',
        
        warm_start_enabled=False,
        num_training_steps=2000
        
    )),
    
    'Tseep 850K': Settings(BASE_TSEEP_SETTINGS, Settings(
        
        dataset_name='Tseep 850K',
        
        # These are ignored when `warm_start_enabled` is `False`.
        # They are for a `waveform_duration` of .190.
        spectrogram_clipping_min=-1.600000023841858,
        spectrogram_clipping_max=24.100000381469727,
        spectrogram_normalization_scale_factor=0.31346933450652303,
        spectrogram_normalization_offset=-4.265454903782186,
        
        warm_start_enabled=False,
        num_training_steps=20000

    )),
    
    'Tseep 2.5M': Settings(BASE_TSEEP_SETTINGS, Settings(
        
        dataset_name='Tseep 2.5M',
        
        # These are ignored when `warm_start_enabled` is `False`.
        # They are for a `waveform_duration` of .190.
        spectrogram_clipping_min=-1.399999976158142,
        spectrogram_clipping_max=24.0,
        spectrogram_normalization_scale_factor=0.31422293126916384,
        spectrogram_normalization_offset=-4.274807996653199,
        
        warm_start_enabled=False,
        num_training_steps=20000

    )),
    
    'Tseep 2.5M 1.5x': Settings(BASE_TSEEP_SETTINGS, Settings(
        
        dataset_name='Tseep 2.5M',
        
        # These are ignored when `warm_start_enabled` is `False`.
        # They are for a `waveform_duration` of .190.
        spectrogram_clipping_min=-1.399999976158142,
        spectrogram_clipping_max=24.100000381469727,
        spectrogram_normalization_scale_factor=0.31394569403171235,
        spectrogram_normalization_offset=-4.2632720810753115,
        
        warm_start_enabled=False,
        num_training_steps=20000

    )),
    
    'Thrush Quick': Settings(BASE_THRUSH_SETTINGS, Settings(
        dataset_name='Thrush 100K',
        pretraining_num_examples=1000,
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16],
        num_training_steps=1000
    )),    
    
    'Thrush Baseline': Settings(BASE_THRUSH_SETTINGS, Settings(
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16],
    )),
    
    'Thrush 600K': Settings(BASE_THRUSH_SETTINGS, Settings(
        
        # These are ignored when `warm_start_enabled` is `False`.
        # They are for a `waveform_duration` of .250.
        spectrogram_clipping_min=-0.699999988079071,
        spectrogram_clipping_max=25.0,
        spectrogram_normalization_scale_factor=0.3072209816231628,
        spectrogram_normalization_offset=-4.58638721925296,
        
        warm_start_enabled=False,
        training_batch_size=200,
        num_training_steps=10000
        
    )),    
    
}


def main():
    
    # Set AWS S3 region to access datasets stored on S3.
    os.environ['S3_REGION'] = 'us-east-2'
    
    open_mp_utils.work_around_multiple_copies_issue()
    
    train_and_evaluate_classifier(CLASSIFIER_NAME)
    
    # show_training_dataset(CLASSIFIER_NAME)
    # show_spectrogram_dataset(CLASSIFIER_NAME)
    
    
def train_and_evaluate_classifier(name):
    
    settings = SETTINGS[name]
    
    do_intro(name, settings)
    
    settings = complete_settings(settings)
    show_preprocessing_settings(settings)
    
    classifier = Classifier(name, settings)
    classifier.train()
    classifier.evaluate()
    classifier.save()
    
    print('Training script is complete.')
    script_utils.announce('Harold, your training script has finished.')


def do_intro(name, settings):
    
    start_type = 'warm' if settings.warm_start_enabled else 'cold'
    model_dir_path = get_model_dir_path(name)
    
    if start_type == 'cold' or not model_dir_path.exists():
        
        print(
            'This script will train classifier "{}" with a cold start.'.format(
                name))
        
        if model_dir_path.exists():
            
            print(
                'It will delete the existing model directory "{}".'.format(
                    model_dir_path))
            
        else:
            # model directory does not exist
            
            print(
                'It will create a new model directory "{}".'.format(
                    model_dir_path))
        
    else:
        # warm start
        
        print((
            'This script will train classifier "{}" with a warm start from '
            'model directory "{}".').format(name, model_dir_path))
    
    # Give user a chance to abort.
    input('Press Enter to continue...')
    
    if start_type == 'cold' and model_dir_path.exists():
        print('Deleting model directory "{}"...'.format(model_dir_path))
        shutil.rmtree(model_dir_path)
    

def get_model_dir_path(name):
    return MODELS_DIR_PATH / name


def get_saved_models_dir_path(name):
    return get_model_dir_path(name) / SAVED_MODELS_DIR_NAME


def complete_settings(settings):
    
    # Copy settings so we don't modify the originals.
    s = Settings(settings)
    
    # Get the nominal start time of the portion of a dataset waveform
    # that is used for training. When time shifting waveform modification
    # is enabled, a random offset is added to the nominal start time
    # for each training example to determine the actual start time.
    s.waveform_start_time = \
        s.event_onset_window_start_time - s.waveform_initial_padding
        
    if s.spectrogram_clipping_enabled and \
            s.spectrogram_clipping_pretraining_enabled and \
            not s.warm_start_enabled:
        
        min_value, max_value = compute_spectrogram_clipping_settings(s)
        
        s.spectrogram_clipping_min = min_value
        s.spectrogram_clipping_max = max_value
        
    if s.spectrogram_normalization_enabled and \
            s.spectrogram_normalization_pretraining_enabled and \
            not s.warm_start_enabled:
        
        scale_factor, offset = compute_spectrogram_normalization_settings(s)
        
        s.spectrogram_normalization_scale_factor = scale_factor
        s.spectrogram_normalization_offset = offset
        
    return s
            

def compute_spectrogram_clipping_settings(settings):
    
    # Get new settings with spectrogram clipping and normalization disabled.
    s = Settings(
        settings,
        spectrogram_clipping_enabled=False,
        spectrogram_normalization_enabled=False)
    
    num_examples = s.pretraining_num_examples
    batch_size = s.pretraining_batch_size
    num_batches = int(round(num_examples / batch_size))
    
    hist_min = s.pretraining_histogram_min
    hist_max = s.pretraining_histogram_max
    num_bins = s.pretraining_histogram_num_bins
    bin_size = (hist_max - hist_min) / num_bins
    log_epsilon = math.log(settings.spectrogram_log_epsilon)
    
    dataset = create_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, DATASET_MODE_TRAINING, s,
        batch_size=batch_size)
    
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        print(
            'Computing spectrogram clipping range from {} examples...'.format(
                num_batches * batch_size))
        
        start_time = time.time()
        
        histogram = np.zeros(num_bins)
        
        for _ in range(num_batches):
                
            features, _ = session.run(next_batch)
            grams = features['spectrogram']
            
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
            
        elapsed_time = time.time() - start_time
        print(
            'Computed spectrogram clipping range in {:.1f} seconds.'.format(
                elapsed_time))

    # Plot spectrogram value distribution and clipping limits.
    if s.pretraining_value_distribution_plotting_enabled:
        distribution = histogram / histogram.sum()
        plt.figure(1)
        plt.plot(edges[:-1], distribution)
        plt.axvline(min_value, color='r')
        plt.axvline(max_value, color='r')
        plt.xlim((edges[0], edges[-1]))
        plt.title('Distribution of Spectrogram Values')
        plt.xlabel('Log Power')
        plt.show()

    # The float conversions in the following ensure that the assigned
    # type is Python's `float` instead of a NumPy type. The latter
    # doesn't play nicely with `yaml_utils.dump`.
    min_value = float(min_value)
    max_value = float(max_value)
    
    return min_value, max_value
    
    
def create_spectrogram_dataset(
        dataset_name, dataset_part, dataset_mode, settings, num_repeats=1,
        shuffle=False, batch_size=1, feature_name='spectrogram'):
    
    dir_path = DATASETS_DIR_PATH / dataset_name / dataset_part
    
    return dataset_utils.create_spectrogram_dataset_from_waveform_files(
        dir_path, dataset_mode, settings, num_repeats, shuffle, batch_size,
        feature_name)


def compute_spectrogram_normalization_settings(settings):
    
    # Get new settings with spectrogram normalization disabled.
    s = Settings(settings, spectrogram_normalization_enabled=False)
    
    num_examples = s.pretraining_num_examples
    batch_size = s.pretraining_batch_size
    num_batches = int(round(num_examples / batch_size))
    
    dataset = create_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, DATASET_MODE_TRAINING, s,
        batch_size=batch_size)

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
                
            features, _ = session.run(next_batch)
            grams = features['spectrogram']
            
            num_values += grams.size
            values_sum += grams.sum()
            squares_sum += (grams ** 2).sum()
            
            mean = values_sum / num_values
            std_dev = math.sqrt(squares_sum / num_values - mean ** 2)
            
            # print(
            #     'Batch {} of {}: ({}, {})'.format(
            #         i + 1, num_batches, mean, std_dev))
            
        elapsed_time = time.time() - start_time
        print((
            'Computed spectrogram normalization settings in {:.1f} '
            'seconds.').format(elapsed_time))
        
    # The float conversions in the following ensure that the assigned
    # type is Python's `float` instead of a NumPy type. The latter
    # doesn't play nicely with `yaml_utils.dump`.
    scale_factor = float(1 / std_dev)
    offset = float(-mean / std_dev)
    
    return scale_factor, offset

    
def show_preprocessing_settings(settings):
    
    s = settings
    
    if s.spectrogram_clipping_enabled:
        
        print(
            'Spectrogram clipping is enabled with range ({}, {}).'.format(
                s.spectrogram_clipping_min, s.spectrogram_clipping_max))
        
    else:
        print('Spectrogram clipping is disabled.')
        
    if s.spectrogram_normalization_enabled:
        
        print((
            'Spectrogram normalization is enabled with scale factor {} '
            'and offset {}.').format(
                s.spectrogram_normalization_scale_factor,
                s.spectrogram_normalization_offset))
        
    else:
        print('Spectrgram normalization is disabled.')
        
        
class Classifier:
    
    
    def __init__(self, name, settings):
        
        self.name = name
        self.settings = settings
        
        self.model = create_model(self.settings)
        self.estimator = self._create_estimator()
        
        
    @property
    def model_dir_path(self):
        return get_model_dir_path(self.name)
    
    
    @property
    def model_input_name(self):
        
        """
        The name assigned by the Keras model to its input.
        
        We use this as a feature name in training and evaluation datasets
        to tell TensorFlow what data to feed to the model.
        """
        
        return self.model.input_names[0]
    
    
    def _create_estimator(self):
        
        config = tf.estimator.RunConfig(
            save_summary_steps=100,
            save_checkpoints_steps=200,
            keep_checkpoint_max=None)
        
        return tf.keras.estimator.model_to_estimator(
            self.model,
            model_dir=self.model_dir_path,
            config=config)
        
        
    def train(self):
        
        s = self.settings
        
        print(
            'Training classifier to {} steps...'.format(s.num_training_steps))
        
        train_spec = tf.estimator.TrainSpec(
            input_fn=self._create_training_dataset,
            max_steps=s.num_training_steps)
        
        eval_spec = tf.estimator.EvalSpec(
            input_fn=self._create_validation_dataset,
            steps=None,
            start_delay_secs=30,
            throttle_secs=30)
        
        start_time = time.time()
        
        tf.estimator.train_and_evaluate(self.estimator, train_spec, eval_spec)
        
        elapsed_time = time.time() - start_time
        
        if not s.warm_start_enabled:
            rate = s.num_training_steps / elapsed_time
            rate_text = ', a rate of {:.1f} steps per second'.format(rate)
        else:
            rate_text = ''
            
        print((
            'Training took {:.1f} seconds to {} steps{}.').format(
                elapsed_time, s.num_training_steps, rate_text))


    def evaluate(self):
        
        print('Evaluating classifier on training dataset...')
        
        self.train_stats = \
            self._evaluate(self._create_evaluation_training_dataset)
            
        print('Evaluating classifier on validation dataset...')
        
        self.val_stats = self._evaluate(self._create_validation_dataset)
        
        print('Saving results...')
        
        save_results(
            self.name, self.train_stats, self.val_stats, self.settings)
        
        print('Done saving results.')
            
        
    def _evaluate(self, dataset_creator, num_thresholds=101):
        
        labels = get_dataset_labels(dataset_creator())
        
        start_time = time.time()
        
        scores = classifier_utils.score_dataset_examples(
            self.estimator, dataset_creator)
        
        elapsed_time = time.time() - start_time
        num_slices = len(scores)
        rate = num_slices / elapsed_time
        print((
            'Evaluated classifier on {} waveform slices in {:.1f} seconds, '
            'a rate of {:.1f} slices per second.').format(
                num_slices, elapsed_time, rate))
            
        thresholds = np.arange(num_thresholds) / float(num_thresholds - 1)
    
        return BinaryClassificationStats(labels, scores, thresholds)
        
        
    def _create_training_dataset(self):
        return self._create_dataset(
            DATASET_PART_TRAINING, DATASET_MODE_TRAINING, num_repeats=None,
            shuffle=True)
    
    
    def _create_dataset(
            self, dataset_part, dataset_mode, num_repeats=1, shuffle=False):
        
        s = self.settings
        
        return create_spectrogram_dataset(
            s.dataset_name, dataset_part, dataset_mode, s,
            num_repeats=num_repeats, shuffle=shuffle,
            batch_size=s.training_batch_size,
            feature_name=self.model_input_name)
        
        
    def _create_evaluation_training_dataset(self):
        return self._create_dataset(
            DATASET_PART_TRAINING, DATASET_MODE_EVALUATION)


    def _create_validation_dataset(self):
        return self._create_dataset(
            DATASET_PART_VALIDATION, DATASET_MODE_EVALUATION)
        
        
    def save(self):
        
        print('Saving model...')
        
        models_dir_path = get_saved_models_dir_path(self.name)
        model_dir_path = self._save_tensorflow_model(models_dir_path)
        self._save_keras_model(model_dir_path)
        self._save_settings(model_dir_path)
        
        print('Saved model to directory "{}".'.format(model_dir_path))

        
    def _save_tensorflow_model(self, models_dir_path):
        
        input_name = self.model_input_name
        input_shape = self.model.get_layer(index=0).input_shape
        
        serving_input_receiver_fn = \
            tf.estimator.export.build_raw_serving_input_receiver_fn({
                input_name:
                    tf.placeholder(dtype=tf.float32, shape=input_shape)
            })
    
        # We export a TensorFlow SavedModel that can be used only in
        # predict mode, but not train or eval mode, since we expect
        # to use the model only for prediction (i.e. inference).
        # If that changes in the future, see the documentation for
        # tf.contrib.estimator.SavedModelEstimator for how to save
        # a model for all three modes.
        model_dir_path = self.estimator.export_saved_model(
            str(models_dir_path), serving_input_receiver_fn)
        
        # For some reason `export_saved_model` returns a `bytes` object
        # instead of a `str` object. We need a `str` object for the `Path`
        # initializer.
        model_dir_path = model_dir_path.decode()
        
        return Path(model_dir_path)
        

    def _save_keras_model(self, model_dir_path):
        
        # We save a Keras model even though we don't use it ourselves,
        # since somebody else might prefer it to a TensorFlow model.
        
        file_path = model_dir_path / classifier_utils.KERAS_MODEL_FILE_NAME
        self.model.save(str(file_path))


    def _save_settings(self, dir_path):
        
        # Find classification threshold and add it to settings.
        self.settings.classification_threshold = find_classification_threshold(
            self.val_stats, self.settings.min_classifier_recall)
        
        # Add TensorFlow model input name to settings.
        self.settings.model_input_name = self.model_input_name
        
        # Save settings.
        settings = self.settings.__dict__
        text = yaml_utils.dump(settings, default_flow_style=False)
        file_path = dir_path / classifier_utils.SETTINGS_FILE_NAME
        file_path.write_text(text)
                    

def create_model(settings):
    
    print('Creating classifier model...')
    
    regularizer = create_regularizer(settings)
    
    model = tf.keras.Sequential()
    add_convolutional_layers(model, settings, regularizer)
    add_hidden_dense_layers(model, settings, regularizer)
    add_output_layer(model, settings, regularizer)
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    print('Done creating classifier model.')
    
    return model

        
def create_regularizer(settings):
    
    if settings.l2_regularization_enabled:
        
        beta = settings.l2_regularization_beta
        
        print((
            'Loss will include L2 regularization term with beta of '
            '{}.').format(beta))
        
        return tf.keras.regularizers.l2(beta)
    
    else:
        return None
        

def add_convolutional_layers(model, settings, regularizer):
    
    num_layers = len(settings.convolutional_layer_sizes)
    
    for layer_num in range(num_layers):
        
        layer_size = settings.convolutional_layer_sizes[layer_num]
        
        kwargs = {
            'name': 'Conv2D_' + str(layer_num),
            'filters': layer_size,
            'kernel_size': (3, 3),
            'activation': 'relu',
            'kernel_regularizer': regularizer
        }
        
        if layer_num == 0:
            # first network layer
            
            # Specify input shape. The added dimension is for channel.
            spectrogram_shape = \
                dataset_utils.get_sliced_spectrogram_shape(settings)
            kwargs['input_shape'] = spectrogram_shape + (1,)
            
        model.add(tf.keras.layers.Conv2D(**kwargs))
        
        print(
            'Added convolutional layer with {} kernels.'.format(layer_size))
        
        if settings.batch_normalization_enabled:
            model.add(tf.keras.layers.BatchNormalization())
            print('Added batch normalization layer.')
        
        model.add(tf.keras.layers.MaxPooling2D(pool_size=(2, 2)))
        print('Added max pooling layer.')

    if num_layers != 0:
        model.add(tf.keras.layers.Flatten())
        print('Added flattening layer.')

    
def add_hidden_dense_layers(model, settings, regularizer):
    
    num_layers = len(settings.dense_layer_sizes)
    
    for layer_num in range(num_layers):
        
        layer_size = settings.dense_layer_sizes[layer_num]
        
        kwargs = {
            'name': 'Dense_' + str(layer_num),
            'units': layer_size,
            'activation': 'relu',
            'kernel_regularizer': regularizer
        }
         
        if layer_num == 0 and len(settings.convolutional_layer_sizes) == 0:
            # first network layer
            
            kwargs['input_dim'] = \
                dataset_utils.get_sliced_spectrogram_size(settings)
             
        model.add(tf.keras.layers.Dense(**kwargs))
        
        print('Added dense layer with {} neurons.'.format(layer_size))
        
        if settings.batch_normalization_enabled:
            model.add(tf.keras.layers.BatchNormalization())
            print('Added batch normalization layer.')
            

def add_output_layer(model, settings, regularizer):
    
    kwargs = {
        'name': 'Output',
        'units': 1,
        'activation': 'sigmoid',
        'kernel_regularizer': regularizer
    }
    
    if len(settings.convolutional_layer_sizes) == 0 and \
            len(settings.dense_layer_sizes) == 0:
        # output layer is only network layer (i.e. the network will
        # have a single neuron and perform logistic regression)
        
        kwargs['input_dim'] = \
            dataset_utils.get_sliced_spectrogram_size(settings)

    model.add(tf.keras.layers.Dense(**kwargs))
    
    print('Added output layer.')
    

def get_dataset_labels(dataset):
    
    iterator = dataset.make_one_shot_iterator()
    next_batch = iterator.get_next()
     
    with tf.Session() as session:
        
        label_batches = []
        num_labels = 0
        
        while True:
            
            try:
                _, labels = session.run(next_batch)
                labels = labels.flatten()
                label_batches.append(labels.flatten())
                num_labels += labels.size
                
            except tf.errors.OutOfRangeError:
                break
            
    return np.concatenate(label_batches)
    
    
def save_results(classifier_name, train_stats, val_stats, settings):
    plot_precision_recall_curves(
        classifier_name, train_stats, val_stats, settings)
    plot_roc_curves(classifier_name, train_stats, val_stats)
    write_precision_recall_csv_file(classifier_name, train_stats, val_stats)
        
        
def plot_precision_recall_curves(
        classifier_name, train_stats, val_stats, settings):
    
    file_path = create_results_file_path(
        PR_PLOT_FILE_NAME_FORMAT, classifier_name)
    
    with PdfPages(file_path) as pdf:
        
        plt.figure(figsize=(6, 6))
        
        # Plot training and validation curves.
        plt.plot(
            train_stats.recall, train_stats.precision, 'b',
            val_stats.recall, val_stats.precision, 'g')
        
        # Set title, legend, and axis labels.
        plt.title('{} Precision vs. Recall'.format(classifier_name))
        plt.legend(['Training', 'Validation'])
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        
        # Set axis limits.
        lower_limit = settings.precision_recall_plot_lower_axis_limit
        plt.xlim((lower_limit, 1))
        plt.ylim((lower_limit, 1))
        
        # Configure grid.
        major_locator = MultipleLocator(
            settings.precision_recall_plot_major_tick_interval)
        minor_locator = MultipleLocator(
            settings.precision_recall_plot_minor_tick_interval)
        axes = plt.gca()
        axes.xaxis.set_major_locator(major_locator)
        axes.xaxis.set_minor_locator(minor_locator)
        axes.yaxis.set_major_locator(major_locator)
        axes.yaxis.set_minor_locator(minor_locator)
        plt.grid(which='both')
        plt.grid(which='minor', alpha=.4)

        pdf.savefig()
        
        plt.close()


def create_results_file_path(file_name_format, classifier_name):
    file_name = file_name_format.format(classifier_name)
    return RESULTS_DIR_PATH / file_name


def plot_roc_curves(classifier_name, train_stats, val_stats):
    
    file_path = create_results_file_path(
        ROC_PLOT_FILE_NAME_FORMAT, classifier_name)
    
    with PdfPages(file_path) as pdf:
        
        plt.figure(figsize=(6, 6))
    
        # Plot training and validation curves.
        plt.plot(
            train_stats.false_positive_rate, train_stats.true_positive_rate,
            'b', val_stats.false_positive_rate, val_stats.true_positive_rate,
            'g')
        
        # Set title, legend, and axis labels.
        plt.title('{} ROC'.format(classifier_name))
        plt.legend(['Training', 'Validation'])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        
        # Set axis limits.
        plt.xlim((0, 1))
        plt.ylim((0, 1))
        
        # Configure grid.
        major_locator = MultipleLocator(.25)
        minor_locator = MultipleLocator(.05)
        axes = plt.gca()
        axes.xaxis.set_major_locator(major_locator)
        axes.xaxis.set_minor_locator(minor_locator)
        axes.yaxis.set_major_locator(major_locator)
        axes.yaxis.set_minor_locator(minor_locator)
        plt.grid(which='both')
        plt.grid(which='minor', alpha=.4)
    
        pdf.savefig()
        
        plt.close()


def write_precision_recall_csv_file(classifier_name, train_stats, val_stats):
    
    file_path = create_results_file_path(
        PR_CSV_FILE_NAME_FORMAT, classifier_name)
    
    with open(file_path, 'w') as csv_file:
        
        csv_file.write(PR_CSV_FILE_HEADER)
        
        columns = (
            train_stats.threshold,
            train_stats.recall,
            train_stats.precision,
            val_stats.recall,
            val_stats.precision
        )
        
        for row in zip(*columns):
            csv_file.write(PR_CSV_FILE_ROW_FORMAT.format(*row))


def find_classification_threshold(stats, min_recall):
    
    # Find index of last recall that is at least `min_recall`.
    # `stats.recall` is nonincreasing, so we flip it before using
    # `bisect.bisect_left`, and then flip the resulting index.
    recalls = np.flipud(stats.recall)
    i = bisect.bisect_left(recalls, min_recall)
    i = len(recalls) - 1 - i
    
    # The float conversion in the following ensures that the assigned
    # type is Python's `float` instead of a NumPy type. The latter
    # doesn't play nicely with `yaml_utils.dump`.
    threshold = float(stats.threshold[i])
    
#     print('recalls', stats.recall)
#     print('thresholds', stats.threshold)
#     print(min_recall, i, threshold, threshold.__class__.__name__)
    
    return threshold


def show_training_dataset(classifier_name):
    
    settings = get_completed_settings(classifier_name)
    
    dataset = create_spectrogram_dataset(
        settings.dataset_name, DATASET_PART_TRAINING, DATASET_MODE_TRAINING,
        settings)
    
    dataset_utils.show_dataset(dataset, 20)
        
    
def get_completed_settings(classifier_name):
    return complete_settings(SETTINGS[classifier_name])


def show_spectrogram_dataset(classifier_name):
    
    total_num_examples = 2 ** 9
    batch_size = 2 ** 6
    
    settings = get_completed_settings(classifier_name)
    
    # Show unclipped and unnormalized spectrograms.
    s = Settings(
        settings,
        spectrogram_clipping_enabled=False,
        spectrogram_normalization_enabled=False)
    
    dataset = create_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, DATASET_MODE_TRAINING, s,
        batch_size=batch_size)
    
    num_batches = int(round(total_num_examples / batch_size))
    dataset_utils.show_dataset(dataset, num_batches)


if __name__ == '__main__':
    main()
