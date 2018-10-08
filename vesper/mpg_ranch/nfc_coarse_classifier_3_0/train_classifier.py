# The following commented code was an attempt (along with setting the
# PYTHONHASHSEED environment variable to 0 in the PyDev run configuration
# for this script) to make classifier training reproducible, but it didn't
# work.
# 
# import random
# random.seed(1)
#  
# import numpy as np
# np.random.seed(1)
#  
# import tensorflow as tf
# tf.set_random_seed(1)

from pathlib import Path
# import copy
import pickle
import sys
import time

from keras.models import Sequential
from keras.layers import Conv2D, Dense, Flatten, MaxPooling2D
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import keras
import matplotlib.pyplot as plt
import numpy as np
import yaml

from vesper.mpg_ranch.nfc_coarse_classifier_3_0.feature_computer import \
    FeatureComputer
from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.util.bunch import Bunch
from vesper.util.clips_hdf5_file import ClipsHdf5File
from vesper.util.conditional_printer import ConditionalPrinter
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier_utils as \
    classifier_utils
import vesper.util.numpy_utils as numpy_utils


# TODO: Offer reproducible training option.
# TODO: Balance data in training epochs.
# TODO: Try using longer thrush waveforms.
# TODO: Try learning a filter bank instead of using a spectrogram.
# TODO: Try lots of random sets of hyperparameter values.
# TODO: Try training several networks and using majority vote of best three.


_CLIPS_FILE_PATH = '/Users/harold/Desktop/2017 {} Clips 22050.h5'

_VERBOSE = True

_TRAIN_CNN = False

# Progress notification period for clip reading and spectrogram computation
# when output is verbose, in clips.
_NOTIFICATION_PERIOD = 10000

_SETTINGS = {
     
    'Tseep': Settings(
        
        clip_type='Tseep',
        
        waveform_start_time=.080,
        waveform_duration=.150,
        
        spectrogram_window_size=.005,
        spectrogram_hop_size=.0025,
        spectrogram_start_freq=4000,
        spectrogram_end_freq=10000,
        spectrogram_power_clipping_fraction=.001,
        spectrogram_normalization_enabled=True,
        
        min_recall=.98,
        
        training_set_size=100000,
        validation_set_size=5000,
        test_set_size=5000,
        
        num_epochs=20,
        batch_size=128,
        
        # Sizes in units of the hidden layers of the classification
        # neural network. All of the hidden layers are dense, and all
        # use the RELU activation function. The final layer of the
        # network comprises a single unit with a sigmoid activation
        # function. Setting this to the empty list yields a logistic
        # regression classifier.
        hidden_layer_sizes=[16],
        
        regularization_beta=.002
        
    ),
             
    'Thrush': Settings(
        
        clip_type='Thrush',
        
        waveform_start_time=.150,
        waveform_duration=.175,
        
        spectrogram_window_size=.005,
        spectrogram_hop_size=.0025,
        spectrogram_start_freq=2000,
        spectrogram_end_freq=5000,
        spectrogram_power_clipping_fraction=.001,
        spectrogram_normalization_enabled=True,
        
        min_recall=.97,
        
        training_set_size=None,
        validation_set_size=5000,
        test_set_size=5000,
        
        num_epochs=40,
        batch_size=128,
        
        # Sizes in units of the hidden layers of the classification
        # neural network. All of the hidden layers are dense, and all
        # use the RELU activation function. The final layer of the
        # network comprises a single unit with a sigmoid activation
        # function. Setting this to the empty list yields a logistic
        # regression classifier.
        hidden_layer_sizes=[16],
        
        # Got the following results for training networks of various
        # sizes on 2017-11-15:
        #
        #     [8] 0.07 0.971 0.801
        #     [10] 0.14 0.971 0.865
        #     [12] 0.12 0.970 0.819
        #     [14] 0.08 0.971 0.801
        #     [16] 0.06 0.972 0.805
        #     [18] 0.15 0.970 0.866
        #     [20] 0.09 0.973 0.815
        #     [22] 0.11 0.970 0.849
        #     [24] 0.11 0.972 0.858
        # 
        #     [8] 0.09 0.971 0.833
        #     [10] 0.08 0.972 0.790
        #     [12] 0.11 0.971 0.851
        #     [14] 0.11 0.971 0.841
        #     [16] 0.09 0.972 0.834
        #     [18] 0.16 0.970 0.819
        #     [20] 0.13 0.971 0.852
        #     [22] 0.11 0.971 0.847
        #     [24] 0.12 0.971 0.833
        # 
        #     [8] 0.09 0.970 0.842
        #     [10] 0.09 0.970 0.846
        #     [12] 0.12 0.972 0.838
        #     [14] 0.11 0.971 0.833
        #     [16] 0.10 0.971 0.824
        #     [18] 0.08 0.972 0.837
        #     [20] 0.11 0.970 0.838
        #     [22] 0.08 0.971 0.850
        #     [24] 0.10 0.971 0.823
        
        # hidden_layer_sizes=[
        #    [8], [10], [12], [14], [16], [18], [20], [22], [24]
        # ],
        
        regularization_beta=.002
        
    )
             
             
}


def _main():
    
    clip_type = sys.argv[1]
    
    # _test_save_stats(clip_type)
    # return

    # _show_stats_pickle_file(clip_type)
    # return
    
    settings = _SETTINGS[clip_type]
    
    clips_file_path = Path(_CLIPS_FILE_PATH.format(clip_type))
    clips = _get_clips(clips_file_path, settings)
    
    if not _VERBOSE:
        print('Computing features...')
    features = _compute_features(clips, settings)
    
    print('Getting targets from classifications...')
    targets = _get_targets(clips)
    
    print('Creating training, validation, and test data sets...')
    train_set, val_set, _ = _create_data_sets(features, targets, settings)
        
#     print('Training classifiers...')
#     _train_classifiers(train_set, val_set, settings)
    
    print('Training classifier...')
    model = _train_classifier(train_set, settings)
    
    print('Testing classifier...')
    train_stats = _test_classifier(model, train_set)
    val_stats = _test_classifier(model, val_set)
    _show_stats(clip_type, train_stats, val_stats)

    print('Saving classifier...')
    _save_classifier(model, settings, train_stats, val_stats)
       
    print()
        

def _get_clips(file_path, settings):
    
    file_ = ClipsHdf5File(file_path)
    
    num_file_clips = file_.get_num_clips()
    
    num_clips = _get_num_read_clips(num_file_clips, settings)
    
    if num_clips != num_file_clips:
        s = '{} of {}'.format(num_clips, num_file_clips)
    else:
        s = '{}'.format(num_clips)
    print('Reading {} clips from file "{}"...'.format(s, file_path))
    
    if _VERBOSE:
        start_time = time.time()
    
    listener = (lambda n: print('    {}'.format(n))) if _VERBOSE else None
    clips = file_.read_clips(num_clips, _NOTIFICATION_PERIOD, listener)
        
    if _VERBOSE:
        
        elapsed_time = time.time() - start_time
        elapsed_time = int(round(10 * elapsed_time)) / 10
        
        if elapsed_time != 0:
            rate = num_clips / elapsed_time
            s = ', an average of {:.1f} clips per second'.format(rate)
        else:
            s = ''
        
        print('Read {} clips in {:.1f} seconds{}.'.format(
            len(clips), elapsed_time, s))
    
        num_calls = len(
            [c for c in clips if c.classification.startswith('Call')])
        num_noises = num_clips - num_calls
        print('Clips include {} calls and {} noises.'.format(
            num_calls, num_noises))
    
    settings.waveform_sample_rate = file_.get_sample_rate()
    
    return clips
        
        
def _get_num_read_clips(num_file_clips, settings):
    
    train_size = settings.training_set_size
    val_size = settings.validation_set_size
    test_size = settings.test_set_size
    
    if train_size is None:
    
        if num_file_clips <= val_size + test_size:
            
            raise ValueError((
                'File contains {} clips, fewer than required '
                'with the specified validation and test set sizes '
                'of {} and {} clips, respectively.').format(
                    num_file_clips, val_size, test_size))
            
        return num_file_clips
            
    else:
        
        num_clips = train_size + val_size + test_size
        
        if num_clips > num_file_clips:
            
            raise ValueError((
                'File contains {} clips, too few for the '
                'specified training, validation, and test set '
                'sizes of {}, {}, and {} clips, respectively.').format(
                    num_file_clips, train_size, val_size, test_size))
            
        return num_clips
    
        
def _compute_features(clips, settings):
    
    vprint = ConditionalPrinter(_VERBOSE)
    
    vprint('Collecting waveforms...')
    waveforms = _collect_waveforms(clips)
    num_waveforms = len(waveforms)
    
    fc = FeatureComputer(settings)
    
    vprint('Trimming waveforms...')
    waveforms = fc.trim_waveforms(waveforms)
    
    def show_clip_count(n):
        vprint('    {}'.format(n))

    vprint('Computing spectrograms...')
    start_time = time.time()
    spectrograms = fc.compute_spectrograms(
        waveforms, _NOTIFICATION_PERIOD, show_clip_count)
    elapsed_time = time.time() - start_time
    spectrogram_rate = num_waveforms / elapsed_time
    spectrum_rate = spectrogram_rate * spectrograms[0].shape[0]
    vprint((
        'Computed {} spectrograms of shape {} in {:.1f} seconds, an '
        'average of {:.1f} spectrograms and {:.1f} spectra per '
        'second.').format(
            num_waveforms, spectrograms[0].shape, elapsed_time,
            spectrogram_rate, spectrum_rate))
    
    vprint('Trimming spectrogram frequencies...')
    vprint('    input shape {}'.format(spectrograms.shape))
    spectrograms = fc.trim_spectrograms(spectrograms)
    vprint('    output shape {}'.format(spectrograms.shape))
    
    fc.configure_spectrogram_power_clipping(spectrograms)
    if settings.spectrogram_min_power is not None:
        vprint('Clipping spectrogram powers to {}...'.format(
            (settings.spectrogram_min_power, settings.spectrogram_max_power)))
        fc.clip_spectrogram_powers(spectrograms)
            
    
    fc.configure_spectrogram_normalization(spectrograms)
    if settings.spectrogram_mean is not None:
        vprint('Normalizing spectrograms with {}...'.format(
            (settings.spectrogram_mean, settings.spectrogram_standard_dev)))
        fc.normalize_spectrograms(spectrograms)
    
    if _TRAIN_CNN:
        return spectrograms
    
    else:
        # training DNN

        vprint('Flattening spectrograms...')
        features = fc.flatten_spectrograms(spectrograms)
         
        return features

    
def _collect_waveforms(clips):
    num_clips = len(clips)
    num_samples = len(clips[0].waveform)
    waveforms = np.zeros((num_clips, num_samples))
    for i, clip in enumerate(clips):
        waveforms[i] = clip.waveform
    return waveforms
        
        
def _get_targets(clips):
    targets = np.array([_get_target(c) for c in clips])
    targets.shape = (len(targets), 1)
    return targets


def _get_target(clip):
    return 1 if clip.classification.startswith('Call') else 0


def _create_data_sets(features, targets, settings):
    
    num_examples = len(features)
    
    assert(len(targets) == num_examples)
    
    train_size = settings.training_set_size
    val_size = settings.validation_set_size
    test_size = settings.test_set_size

    assert(val_size + test_size < num_examples)
    
    if train_size is None:
        train_size = num_examples - val_size - test_size
        
    assert(train_size + val_size + test_size <= num_examples)
    
    # Shuffle examples.
    permutation = numpy_utils.reproducible_permutation(num_examples)
    features = features[permutation]
    targets = targets[permutation]
    
    if _TRAIN_CNN:
        
        # Add extra dimension to features for CNN input.
        features.shape = features.shape + (1,)
    
    test_start = num_examples - test_size
    val_start = test_start - val_size
    
    train_set = Bunch(
        name='training',
        features=features[:val_start],
        targets=targets[:val_start])
    
    val_set = Bunch(
        name='validation',
        features=features[val_start:test_start],
        targets=targets[val_start:test_start])
    
    test_set = Bunch(
        name='test',
        features=features[test_start:],
        targets=targets[test_start:])
    
    return train_set, val_set, test_set


def _train_classifiers(train_set, val_set, settings):
    
    results = []
    
    for hidden_layer_sizes in settings.hidden_layer_sizes:
        
        print('Training classifier with hidden layer sizes {}...'.format(
            hidden_layer_sizes))
        
#         input_length = train_set.features.shape[1]
#         model = _create_dense_classifier_model(
#             input_length, hidden_layer_sizes, settings.regularization_beta)
        
        input_shape = train_set.features.shape[1:]
        model = _create_cnn_classifier_model(input_shape)
        
        verbose = 2 if _VERBOSE else 0
    
        model.fit(
            train_set.features,
            train_set.targets,
            epochs=settings.num_epochs,
            batch_size=settings.batch_size,
            verbose=verbose)

        stats = _test_classifier(model, val_set)
        i = _find_classification_threshold_index(stats, settings.min_recall)
        results.append(
            (hidden_layer_sizes, stats.threshold[i], stats.recall[i],
             stats.precision[i]))
        
    print(
        'Classifier (hidden layer sizes, threshold, recall, precision) '
        'tuples:')
    for r in results:
        print('    {} {:.2f} {:.3f} {:.3f}'.format(*r))
        

# '''
# 
# layers:
#     - {type: Conv2D, filters: 16} 
#     - {type: MaxPooling2D}
#     - {type: Conv2D, filters: 32}
#     - {type: MaxPooling2D}
#     - {type: Flatten}
#     - {type: Dense, units: 32}
#     - {type: Dense, units: 1, activation: 'sigmoid'}
#     
# layer_defaults:
#     Conv2D: {kernel_regularization_beta: null}
#     
# '''
# 
# 
# _DEFAULT_LAYER_DEFAULTS = yaml.load('''
# 
# Conv2D:
#     kernel_size: [3, 3]
#     kernel_regularization_beta: .002
#     activation: relu
#     
# MaxPooling2D: 
#     pool_size: [2, 2]
# 
# Dense:
#     kernel_regularization_beta: .002
#     activation: relu
#     
# ''')
#
#
# def _create_classifier_model(
#         model_spec, input_shape, default_kernel_regularization_beta):
#     
#     default_layer_defaults = _create_default_layer_defaults(
#         default_kernel_regularization_beta=default_kernel_regularization_beta)
#     
#     builtin_defaults = 
#     default_regularizer = keras.regularizers.l2(default_regularization_beta)
#     
#     model = Sequential()
#     
#     layer_specs = model_spec['layers']
#     layer_defaults = model_spec['layer_defaults']
#     
#     for spec in layer_specs:
#         
#     
# def _create_default_layer_defaults(**kwargs):
#     defaults = copy.deepcopy(_DEFAULT_LAYER_DEFAULTS)
#     defaults.update(kwargs)
#     return defaults
    

def _train_classifier(train_set, settings):
    
    if _TRAIN_CNN:
        
        input_shape = train_set.features.shape[1:]
        
        model = _create_cnn_classifier_model(
            input_shape, settings.regularization_beta)
    
    else:
        # training DNN
        
        input_length = train_set.features.shape[1]
        
        model = _create_dnn_classifier_model(
            input_length,
            settings.hidden_layer_sizes,
            settings.regularization_beta)
    
    verbose = 2 if _VERBOSE else 0

    model.fit(
        train_set.features,
        train_set.targets,
        epochs=settings.num_epochs,
        batch_size=settings.batch_size,
        verbose=verbose)
    
    return model
    
       
def _create_cnn_classifier_model(input_shape, regularization_beta):
    
    regularizer = keras.regularizers.l2(regularization_beta)
    
    model = Sequential()
    
#     model.add(Conv2D(
#         16, kernel_size=(3, 3), activation='relu', input_shape=input_shape))
#     model.add(Conv2D(32, (3, 3), activation='relu'))
#     model.add(MaxPooling2D(pool_size=(2, 2)))
#     model.add(Dropout(.25))
#     model.add(Flatten())
#     model.add(Dense(32, activation='relu'))
#     model.add(Dropout(.5))
#     model.add(Dense(1, activation='sigmoid'))
    
    model.add(Conv2D(
        16, kernel_size=(3, 3), activation='relu', input_shape=input_shape,
        kernel_regularizer=regularizer))
    
    # model.add(MaxPooling2D(pool_size=(2, 2)))
    
    model.add(Conv2D(
        32, kernel_size=(3, 3), activation='relu',
        kernel_regularizer=regularizer))
    
    model.add(MaxPooling2D(pool_size=(2, 2)))
    
    model.add(Flatten())
    
    model.add(Dense(32, activation='relu', kernel_regularizer=regularizer))
    
    model.add(Dense(1, activation='sigmoid', kernel_regularizer=regularizer))
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])

    return model

    
def _create_dnn_classifier_model(
        input_length, hidden_layer_sizes, regularization_beta):
    
    layer_sizes = hidden_layer_sizes + [1]
    num_layers = len(layer_sizes)
    
    regularizer = keras.regularizers.l2(regularization_beta)
    
    model = Sequential()
    
    for i in range(num_layers):
        
        kwargs = {
            'activation': 'sigmoid' if i == num_layers - 1 else 'relu',
            'kernel_regularizer': regularizer
        }
        
        if i == 0:
            kwargs['input_dim'] = input_length
            
        model.add(Dense(layer_sizes[i], **kwargs))
        
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    return model
        
    
def _test_classifier(model, data_set, num_thresholds=101):
    
    features = data_set.features
    targets = data_set.targets
    
    values = model.predict(features, batch_size=len(features))
    
    thresholds = np.arange(num_thresholds) / float(num_thresholds - 1)

    return BinaryClassificationStats(targets, values, thresholds)


def _find_classification_threshold_index(stats, min_recall):
    
    recall = stats.recall
    
    i = 0
    while recall[i] >= min_recall:
        i += 1
        
    return i - 1


def _show_stats(clip_type, train_stats, val_stats):
    _show_stats_aux(clip_type, 'training', train_stats)
    print()
    _show_stats_aux(clip_type, 'validation', val_stats)
        
        
def _show_stats_aux(clip_type, name, stats):
    
    print('{} {} (threshold, recall, precision) triples:'.format(
        clip_type, name))
    
    for t, r, p in zip(stats.threshold, stats.recall, stats.precision):
        print('    {:.2f} {:.3f} {:.3f}'.format(t, r, p))
        
        
def _save_classifier(model, settings, train_stats, val_stats):
    
    clip_type = settings.clip_type
    
    path = classifier_utils.get_model_file_path(clip_type)
    path.parent.mkdir(exist_ok=True)
    model.save(path)
    
    settings = _create_classifier_settings(settings, val_stats)
    text = yaml.dump(settings, default_flow_style=False)
    path = classifier_utils.get_settings_file_path(clip_type)
    path.write_text(text)
    
    _save_stats(train_stats, val_stats, clip_type)
    _plot_stats(train_stats, val_stats, clip_type)
    
    
def _create_classifier_settings(s, stats):
    
    return dict(
        
        clip_type=s.clip_type,
        
        waveform_sample_rate=float(s.waveform_sample_rate),
        waveform_start_time=s.waveform_start_time,
        waveform_duration=s.waveform_duration,
        
        spectrogram_window_size=s.spectrogram_window_size,
        spectrogram_hop_size=s.spectrogram_hop_size,
        spectrogram_start_freq=s.spectrogram_start_freq,
        spectrogram_end_freq=s.spectrogram_end_freq,
        spectrogram_min_power=float(s.spectrogram_min_power),
        spectrogram_max_power=float(s.spectrogram_max_power),
        spectrogram_mean=float(s.spectrogram_mean),
        spectrogram_standard_dev=float(s.spectrogram_standard_dev),
        
        classification_threshold=_find_classification_threshold(
            stats, s.min_recall)
        
    )
    
    
def _find_classification_threshold(stats, min_recall):
    i = _find_classification_threshold_index(stats, min_recall)
    return float(stats.threshold[i])


def _test_save_stats(clip_type):
    s = np.arange(101) / 100.
    stats = Bunch(threshold=s, recall=s, precision=s)
    _save_stats(stats, stats, clip_type)


def _show_stats_pickle_file(clip_type):
    
    path = classifier_utils.get_stats_pickle_file_path(clip_type)
    
    with open(path, 'rb') as file_:
        stats = pickle.load(file_)
        
    _show_stats(clip_type, stats.training, stats.validation)
    
    print('accuracy:', stats.training.accuracy)
    
    
_STATS_FORMAT = '''
# Classifier recall and precision statistics for training and validation
# datasets.
#
# Each triple below is of the form:
#
#     [<threshold>, <recall>, <precision>]


training: [
{}
]


validation: [
{}
]
'''.lstrip()


def _save_stats(train_stats, val_stats, clip_type):
    
    # Write YAML file.
    train_text = _get_stats_text(train_stats)
    val_text = _get_stats_text(val_stats)
    text = _STATS_FORMAT.format(train_text, val_text)
    path = classifier_utils.get_stats_yaml_file_path(clip_type)
    path.write_text(text)
    
    # Write pickle file.
    path = classifier_utils.get_stats_pickle_file_path(clip_type)
    stats = Bunch(training=train_stats, validation=val_stats)
    with open(path, 'wb') as file_:
        pickle.dump(stats, file_)
    
    
def _get_stats_text(stats):
    
    lines = [
        _get_stats_text_aux(t, r, p)
        for t, r, p in zip(stats.threshold, stats.recall, stats.precision)]
    
    return ',\n'.join(lines)
    

def _get_stats_text_aux(t, r, p):
    return '    [{:.2f}, {:.3f}, {:.3f}]'.format(t, r, p)


def _plot_stats(train_stats, val_stats, clip_type):

    file_path = classifier_utils.get_plots_file_path(clip_type)
    
    with PdfPages(file_path) as pdf:
        
        plt.figure(figsize=(6, 6))
        
        axes = plt.gca()
        
        # Plot precision vs. recall.
        plt.plot(
            100 * train_stats.precision, 100 * train_stats.recall, 'b',
            100 * val_stats.precision, 100 * val_stats.recall, 'g')
        
        # Set title, axis labels, and legend.
        plt.title('{} Classifier Precision vs. Recall'.format(clip_type))
        plt.xlabel('Recall (%)')
        plt.ylabel('Precision (%)')
        plt.legend(['Training', 'Validation'])
        
        # Set axis limits.
        plt.xlim((90, 100))
        plt.ylim((80, 100))
        
        # Configure grid.
        major_locator = MultipleLocator(5)
        minor_locator = MultipleLocator(1)
        axes.xaxis.set_major_locator(major_locator)
        axes.xaxis.set_minor_locator(minor_locator)
        axes.yaxis.set_major_locator(major_locator)
        axes.yaxis.set_minor_locator(minor_locator)
        plt.grid(which='both')
        plt.grid(which='minor', alpha=.4)
    
        pdf.savefig()
        plt.close()

        plt.figure(figsize=(6, 6))
        plt.plot(
            100 * train_stats.false_positive_rate,
            100 * train_stats.true_positive_rate,
            'b',
            100 * val_stats.false_positive_rate,
            100 * val_stats.true_positive_rate,
            'g')
        plt.title('{} Classifier ROC'.format(clip_type))
        plt.xlabel('False Positive Rate (%)')
        plt.ylabel('True Positive Rate (%)')
        plt.legend(['Training', 'Validation'])
        plt.xlim((0, 100))
        plt.ylim((0, 100))
        pdf.savefig()
        plt.close()
            

if __name__ == '__main__':
    _main()
