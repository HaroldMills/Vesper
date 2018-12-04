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
import yaml

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

from vesper.mpg_ranch.nfc_coarse_classifier_3_0.preprocessor import \
    Preprocessor
from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier_utils as \
    classifier_utils


# TODO: Include both augmented and unaugmented data curves in evaluation plots.
# TODO: Figure out how to save and restore estimator.
# TODO: Build Vesper classifier from saved estimator.
# TODO: Run tseep classifier on all 2017 clips.
# TODO: Look at incorrectly classified clips and reclassify as needed.
# TODO: Prepare Thrush HDF5 files.
# TODO: Train thrush coarse classifier.
# TODO: Try dropout and L2 regularization.
# TODO: Tune hyperparameters.
# TODO: Evaluate on only initial portion of training data.
# TODO: Figure out how to get sequence of training run precision-recall curves.
# TODO: Consider simplifying normalization.


CLASSIFIER_NAME = 'Tseep Quick'

ML_DIR_PATH = Path('/Users/harold/Desktop/NFC/Data/Vesper ML')
DATASETS_DIR_PATH = ML_DIR_PATH / 'Datasets' / 'Coarse Classification'
DATA_FILE_NAME_FORMAT = '{}_{}_{}.tfrecords'

MODELS_DIR_PATH = ML_DIR_PATH / 'Models' / 'Coarse Classification'

RESULTS_DIR_PATH = Path('/Users/harold/Desktop/ML Results')
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

EXAMPLE_FEATURES = {
    'waveform': tf.FixedLenFeature((), tf.string, default_value=''),
    'label': tf.FixedLenFeature((), tf.int64, default_value=0)
}

DATASET_PART_TRAINING = 'Training'
DATASET_PART_VALIDATION = 'Validation'
DATASET_PART_TEST = 'Test'

BASE_TSEEP_SETTINGS = Settings(
    
    dataset_name='Tseep 100K',
    
    sample_rate=24000,
    
    # The onsets of calls in clips created by Vesper's Old Bird Tseep
    # Detector Redux 1.1 occur in a window that starts roughly 90 ms into
    # the clips and is 50 ms wide. The onsets are not uniformly
    # distributed within this window: the location of an onset in the
    # window depends on the strength and bandwidth of the onset, and more
    # onsets occur later in the window than earlier. In the future, I hope
    # to narrow this window in our detector and classifier training datasets,
    # and make the distribution of onsets within the window more uniform.
    #
    # Random waveform time shifting is a data augmentation method that can
    # be applied to distribute training clip event onsets more evenly in
    # time. (An event is whatever tripped a detector to create a training
    # clip, whether or not the event was a call.) When random waveform time
    # shifting is enabled, each dataset waveform is shifted in time by an
    # amount drawn from the uniform distribution over
    # [-max_waveform_time_shift, max_waveform_time_shift] before the
    # waveform is sliced. The distribution of onsets after shifting is the
    # distribution before shifting convolved with the (uniform) shift
    # distribution. Note that this widens the window within which onsets
    # can occur by max_waveform_time_shift seconds on each end.
    
    # location of event onset window in training dataset waveforms
    dataset_onset_window_start_time=.090,
    dataset_onset_window_duration=.050,
    
    # random waveform time shifting data augmentation settings
    random_waveform_time_shifting_enabled=True,
    max_waveform_time_shift=.025,
    
    # waveform settings
    waveform_initial_padding=.030,
    waveform_duration=.200,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=50,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=4000,
    spectrogram_end_freq=10000,
    
    # number of parallel calls for input and spectrogram computation
    num_preproc_parallel_calls=4,
    
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
    training_batch_size=64,
    num_training_steps=50000,
    
    # Whether or not data augmentation is enabled during evaluation.
    # A good rule of thumb is to disable data augmentation when evaluating
    # the trained classifier for coarse classification of Old Bird detector
    # clips, and to enable it when evaluating the trained classifier for
    # detection.
    evaluation_data_augmentation_enabled=True,
    
    # evaluation plot settings
    precision_recall_plot_lower_axis_limit=.80,
    precision_recall_plot_major_tick_interval=.05,
    precision_recall_plot_minor_tick_interval=.01,
    
    # classifier performance settings
    min_classifier_recall=.98
    
)


SETTINGS = {
    
    'Tseep Logistic Regression': Settings(BASE_TSEEP_SETTINGS, Settings(
        convolutional_layer_sizes=[],
        dense_layer_sizes=[],
        l2_regularization_enabled=True,
        precision_recall_plot_lower_axis_limit=0,
        precision_recall_plot_major_tick_interval=.25,
        precision_recall_plot_minor_tick_interval=.05
    )),
    
    'Tseep Baseline': Settings(BASE_TSEEP_SETTINGS, Settings(
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16]
    )),
    
    'Tseep Quick': Settings(BASE_TSEEP_SETTINGS, Settings(
        pretraining_num_examples=1000,
        convolutional_layer_sizes=[],
        dense_layer_sizes=[16],
        num_training_steps=1000,
        precision_recall_plot_lower_axis_limit=0,
        precision_recall_plot_major_tick_interval=.25,
        precision_recall_plot_minor_tick_interval=.05
    )),    
    
    'Tseep': Settings(BASE_TSEEP_SETTINGS, Settings(
        num_training_steps=20000
    )),    
    
    'Tseep No BN': Settings(BASE_TSEEP_SETTINGS, Settings(
        batch_normalization_enabled=False,
        num_training_steps=50000
    )),    
    
    'Tseep 340K': Settings(BASE_TSEEP_SETTINGS, Settings(
        dataset_name='Tseep 340K',
        num_training_steps=50000
    )),    
    
    'Tseep 1M': Settings(BASE_TSEEP_SETTINGS, Settings(
        dataset_name='Tseep 1M',
        batch_size=128,
        num_training_steps=20000
    )),    
    
}


def main():
    
    work_around_openmp_issue()
    
    train_and_evaluate_classifier(CLASSIFIER_NAME)
    
    # show_training_dataset(CLASSIFIER_NAME)
    # show_spectrogram_dataset(CLASSIFIER_NAME)
    
    
def work_around_openmp_issue():

    # Added this 2018-11-13 to work around a problem on macOS involving
    # potential confusion among multiple copies of the OpenMP runtime.
    # The problem only appears to arise when I install TensorFlow using
    # Conda rather than pip. I'm not sure where the multiple copies are
    # coming from. Perhaps Conda and Xcode? See
    # https://github.com/openai/spinningup/issues/16 for an example of
    # another person encountering this issue.
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


def train_and_evaluate_classifier(name):
    settings = get_settings(name)
    classifier = Classifier(name, settings)
    classifier.train()
    classifier.evaluate()
    classifier.save()
    

def get_settings(name):
    
    # Copy settings so we don't modify the originals.
    s = Settings(SETTINGS[name])
    
    s.waveform_start_time = get_waveform_start_time(s)
        
    if s.spectrogram_clipping_enabled and \
            s.spectrogram_clipping_pretraining_enabled:
        
        min_value, max_value = compute_spectrogram_clipping_settings(s)
        
        s.spectrogram_clipping_min = min_value
        s.spectrogram_clipping_max = max_value

        
    if s.spectrogram_normalization_enabled and \
            s.spectrogram_normalization_pretraining_enabled:
        
        scale_factor, offset = compute_spectrogram_normalization_settings(s)
        
        s.spectrogram_normalization_scale_factor = scale_factor
        s.spectrogram_normalization_offset = offset
        
    return s
            

def get_waveform_start_time(settings):
    
    s = settings
    
    start_time = s.dataset_onset_window_start_time - s.waveform_initial_padding
    
    if s.random_waveform_time_shifting_enabled:
        start_time -= s.max_waveform_time_shift
        
    return start_time


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
    
    dataset = create_on_disk_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, Preprocessor.MODE_TRAINING, s,
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
        print(
            'Clipping range is ({:.1f}, {:.1f}).'.format(min_value, max_value))

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
    # doesn't play nicely with `yaml.dump`.
    min_value = float(min_value)
    max_value = float(max_value)
    
    return min_value, max_value
    
    
def create_on_disk_spectrogram_dataset(
        dataset_name, dataset_part, preproc_mode, settings, num_repeats=1,
        shuffle=False, batch_size=1, feature_name='spectrogram'):
    
    dataset = create_on_disk_waveform_dataset(dataset_name, dataset_part)
    
    return create_spectrogram_dataset(
        dataset, preproc_mode, settings, num_repeats, shuffle, batch_size,
        feature_name)


def create_on_disk_waveform_dataset(dataset_name, dataset_part):
    
    file_path_pattern = create_data_file_path(dataset_name, dataset_part, '*')
    
    # Get file paths matching pattern. Sort the paths for consistency.
    file_paths = sorted(tf.gfile.Glob(file_path_pattern))
    
    return tf.data.TFRecordDataset(file_paths).map(parse_example)
            
        
def create_data_file_path(dataset_name, dataset_part, file_num):
    dir_path = DATASETS_DIR_PATH / dataset_name / dataset_part
    file_name = DATA_FILE_NAME_FORMAT.format(
        dataset_name, dataset_part, file_num)
    return str(dir_path / file_name)
    

def parse_example(example_proto):
    
    example = tf.parse_single_example(example_proto, EXAMPLE_FEATURES)
    
    bytes_ = example['waveform']
    waveform = tf.decode_raw(bytes_, out_type=tf.int16, little_endian=True)
    
    label = example['label']
    
    return waveform, label


def create_spectrogram_dataset(
        waveform_dataset, preproc_mode, settings, num_repeats=1,
        shuffle=False, batch_size=1, feature_name='spectrogram'):
    
    preprocessor = Preprocessor(preproc_mode, settings, feature_name)
    
    dataset = waveform_dataset
    
    if num_repeats is None:
        dataset = dataset.repeat()
    elif num_repeats != 1:
        dataset = dataset.repeat(num_repeats)
    
    # waveform_preprocessor = WaveformPreprocessor(preproc_mode, settings)
     
    dataset = dataset.map(
        preprocessor.preprocess_waveform,
        num_parallel_calls=settings.num_preproc_parallel_calls)
    
    if shuffle:
        dataset = dataset.shuffle(10 * batch_size)
        
    if batch_size != 1:
        dataset = dataset.batch(batch_size)
    
    # spectrogram_computer = SpectrogramComputer(
    #     preproc_mode, settings, feature_name)
    
    dataset = dataset.map(
        preprocessor.compute_spectrograms,
        num_parallel_calls=settings.num_preproc_parallel_calls)
    
    return dataset
    

def compute_spectrogram_normalization_settings(settings):
    
    # Get settings with spectrogram normalization disabled.
    s = Settings(settings, spectrogram_normalization_enabled=False)
    
    num_examples = s.pretraining_num_examples
    batch_size = s.pretraining_batch_size
    num_batches = int(round(num_examples / batch_size))
    
    dataset = create_on_disk_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, Preprocessor.MODE_TRAINING, s,
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
        print((
            'Normalization mean and standard deviation are '
            '({:.1f}, {:.1f}).').format(
                mean, std_dev))
        
    # The float conversions in the following ensure that the assigned
    # type is Python's `float` instead of a NumPy type. The latter
    # doesn't play nicely with `yaml.dump`.
    scale_factor = float(1 / std_dev)
    offset = float(-mean / std_dev)
    
    return scale_factor, offset

    
class Classifier:
    
    
    def __init__(self, name, settings):
        
        self.name = name
        self.settings = settings
        
        self.model = create_model(self.settings)
        
        # Remove old model dir path for a cold start.
        shutil.rmtree(self.model_dir_path, ignore_errors=True)
        
        self.estimator = self._create_estimator()
        
        
    @property
    def model_dir_path(self):
        return MODELS_DIR_PATH / self.name
    
    
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
            'Training classifier for {} steps...'.format(
                s.num_training_steps))
        
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
        rate = s.num_training_steps / elapsed_time
        print((
            'Training took {:.1f} seconds for {} steps, a rate of {:.1f} '
            'steps per second.').format(
                elapsed_time, s.num_training_steps, rate))


    def evaluate(self):
        
        print('Evaluating classifier on training dataset...')
        
        self.train_stats = \
            self._evaluate(self._create_evaluation_training_dataset)
            
        print('Evaluating classifier on validation dataset...')
        
        self.val_stats = self._evaluate(self._create_validation_dataset)
        
        print('Saving results...')
        
        save_results(
            self.name, self.train_stats, self.val_stats, self.settings)
        
        print('Done.')
            
        
    def _evaluate(self, dataset_creator, num_thresholds=101):
        
        labels = get_dataset_labels(dataset_creator())
        
        start_time = time.time()
        
        predictions = self.estimator.predict(input_fn=dataset_creator)
        
        # At this point `predictions` is an iterator that yields
        # dictionaries, each of which contains a single item whose
        # value is an array containing one element, a prediction.
        # Extract the predictions into a NumPy array.
        predictions = np.array(
            [list(p.values())[0][0] for p in predictions])
        
        elapsed_time = time.time() - start_time
        num_slices = len(predictions)
        rate = num_slices / elapsed_time
        print((
            'Evaluated classifier on {} waveform slices in {:.1f} seconds, '
            'a rate of {:.1f} slices per second.').format(
                num_slices, elapsed_time, rate))
            
        # pairs = list(zip(labels, predictions))
        # for i, pair in enumerate(pairs[:200]):
        #     print(i, pair)
            
        thresholds = np.arange(num_thresholds) / float(num_thresholds - 1)
    
        return BinaryClassificationStats(labels, predictions, thresholds)
        
        
    def _create_training_dataset(self):
        return self._create_dataset(
            DATASET_PART_TRAINING, Preprocessor.MODE_TRAINING,
            num_repeats=None, shuffle=True)
    
    
    def _create_dataset(
            self, dataset_part, preproc_mode, num_repeats=1, shuffle=False):
        
        s = self.settings
        
        return create_on_disk_spectrogram_dataset(
            s.dataset_name, dataset_part, preproc_mode, s,
            num_repeats=num_repeats, shuffle=shuffle,
            batch_size=s.training_batch_size,
            feature_name=self.model_input_name)
        
        
    def _create_evaluation_training_dataset(self):
        return self._create_dataset(
            DATASET_PART_TRAINING, Preprocessor.MODE_EVALUATION)


    def _create_validation_dataset(self):
        return self._create_dataset(
            DATASET_PART_VALIDATION, Preprocessor.MODE_EVALUATION)
        
        
    def save(self):
        
        clip_type = self.name.split()[0]
        
        path = classifier_utils.get_model_file_path(clip_type)
        path.parent.mkdir(exist_ok=True)
        self.model.save(str(path))

        self.settings.classification_threshold = find_classification_threshold(
            self.val_stats, self.settings.min_classifier_recall)
        
        settings = self.settings.__dict__
        text = yaml.dump(settings, default_flow_style=False)
        path = classifier_utils.get_settings_file_path(clip_type)
        path.write_text(text)

    
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
            'filters': layer_size,
            'kernel_size': (3, 3),
            'activation': 'relu',
            'kernel_regularizer': regularizer
        }
        
        if layer_num == 0:
            # first network layer
            
            # Specify input shape. The added dimension is for channel.
            spectrogram_shape = \
                Preprocessor.get_sliced_spectrogram_shape(settings)
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
            'units': layer_size,
            'activation': 'relu',
            'kernel_regularizer': regularizer
        }
         
        if layer_num == 0 and len(settings.convolutional_layer_sizes) == 0:
            # first network layer
            
            kwargs['input_dim'] = \
                Preprocessor.get_sliced_spectrogram_size(settings)
             
        model.add(tf.keras.layers.Dense(**kwargs))
        
        print('Added dense layer with {} neurons.'.format(layer_size))
        
        if settings.batch_normalization_enabled:
            model.add(tf.keras.layers.BatchNormalization())
            print('Added batch normalization layer.')
            

def add_output_layer(model, settings, regularizer):
    
    kwargs = {
        'units': 1,
        'activation': 'sigmoid',
        'kernel_regularizer': regularizer
    }
    
    if len(settings.convolutional_layer_sizes) == 0 and \
            len(settings.dense_layer_sizes) == 0:
        # output layer is only network layer (i.e. the network will
        # have a single neuron and perform logistic regression)
        
        kwargs['input_dim'] = \
            Preprocessor.get_sliced_spectrogram_size(settings)

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
    recalls = np.flip(stats.recall)
    i = bisect.bisect_left(recalls, min_recall)
    i = len(recalls) - 1 - i
    
    # The float conversion in the following ensures that the assigned
    # type is Python's `float` instead of a NumPy type. The latter
    # doesn't play nicely with `yaml.dump`.
    threshold = float(stats.threshold[i])
    
#     print('recalls', stats.recall)
#     print('thresholds', stats.threshold)
#     print(min_recall, i, threshold, threshold.__class__.__name__)
    
    return threshold


def show_training_dataset(classifier_name):
    
    settings = get_settings(classifier_name)
    
    dataset = create_on_disk_spectrogram_dataset(
        settings.dataset_name, DATASET_PART_TRAINING,
        Preprocessor.MODE_TRAINING, settings)
    
    show_dataset(dataset, 20)
        
    
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
            
        print('Iteration took {} seconds.'.format(time.time() - start_time))
                    

def show_spectrogram_dataset(classifier_name):
    
    total_num_examples = 2 ** 9
    batch_size = 2 ** 6
    
    settings = get_settings(classifier_name)
    
    # Show unclipped and unnormalized spectrograms.
    s = Settings(
        settings,
        spectrogram_clipping_enabled=False,
        spectrogram_normalization_enabled=False)
    
    dataset = create_on_disk_spectrogram_dataset(
        s.dataset_name, DATASET_PART_TRAINING, Preprocessor.MODE_TRAINING, s,
        batch_size=batch_size)
    
    num_batches = int(round(total_num_examples / batch_size))
    show_dataset(dataset, num_batches)


if __name__ == '__main__':
    main()
