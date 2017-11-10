from pathlib import Path
import random
import time

from keras.models import Sequential
from keras.layers import Dense
import keras
import numpy as np

from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.util.bunch import Bunch
from vesper.util.clips_hdf5_file import ClipsHdf5File
from vesper.util.conditional_printer import ConditionalPrinter
from vesper.util.settings import Settings
import vesper.util.data_windows as data_windows
import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


# TODO: Use same training/validation/test split on every run.
# TODO: Balance data in training epochs.
# TODO: Try using longer thrush waveforms.
# TODO: Try adding convolutional layers.
# TODO: Try learning a filter bank instead of using a spectrogram.
# TODO: Try lots of random sets of hyperparameter values.


_DETECTOR_NAME = 'Thrush'

_FILE_PATH = Path(
    '/Users/Harold/Desktop/2017 {} Clips 22050.hdf5'.format(_DETECTOR_NAME))

_SETTINGS = {
     
    'Tseep': Settings(
        
        detector_name='Tseep',
        
        waveform_start_time=.080,
        waveform_duration=.150,
        
        spectrogram_window_size=.005,
        spectrogram_hop_size=.0025,
        spectrogram_start_freq=4000,
        spectrogram_end_freq=10000,
        spectrogram_power_clipping_fraction=.001,
        normalize_spectrograms=True,
        
        training_set_size=90000,
        validation_set_size=5000,
        test_set_size=5000,
        
        num_epochs=5,
        batch_size=128,
        
        # Sizes in units of the hidden layers of the classification
        # neural network. All of the hidden layers are dense, and all
        # use the RELU activation function. The final layer of the
        # network comprises a single unit with a sigmoid activation
        # function. Setting this to the empty list yields a logistic
        # regression classifier.
        hidden_layer_sizes = [16],
        
        regularization_beta=.001,
        
        verbose = True
        
    ),
             
    'Thrush': Settings(
        
        detector_name='Thrush',
        
        waveform_start_time=.150,
        waveform_duration=.175,
        
        spectrogram_window_size = .005,
        spectrogram_hop_size = .0025,
        spectrogram_start_freq=2000,
        spectrogram_end_freq=5000,
        spectrogram_power_clipping_fraction=.001,
        normalize_spectrograms=True,
        
        training_set_size=None,
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
        hidden_layer_sizes = [32, 32],
        
        regularization_beta=.002,
        
        verbose = True
        
    )
             
             
}


def _main():
    
    settings = _SETTINGS[_DETECTOR_NAME]
    
    clips, sample_rate = _get_clips(_FILE_PATH, settings)
    
    if not settings.verbose:
        print('Computing features...')
    features = _compute_features(clips, sample_rate, settings)
    
    print('Getting targets from classifications...')
    targets = _get_targets(clips)
    
    print('Creating training, validation, and test data sets...')
    train_set, val_set, _ = _create_data_sets(features, targets, settings)
        
    print('Training classifier...')
    model = _train_classifier(train_set, settings)
       
    print('Testing classifier...')
    train_stats = _test_classifier(model, train_set)
    val_stats = _test_classifier(model, val_set)
    _show_stats(train_stats, val_stats)

    print()
        

def _get_clips(file_path, settings):
    
    verbose = settings.verbose

    file_ = ClipsHdf5File(file_path)
    
    num_file_clips = file_.get_num_clips()
    
    num_clips = _get_num_read_clips(num_file_clips, settings)
    
    if num_clips != num_file_clips:
        s = '{} of {}'.format(num_clips, num_file_clips)
    else:
        s = '{}'.format(num_clips)
    print('Reading {} clips from file "{}"...'.format(s, file_path))
    
    if verbose:
        start_time = time.time()
    
    notification_period = 10000 if verbose else None
    listener = (lambda n: print('    {}'.format(n))) if verbose else None
    clips = file_.read_clips(num_clips, notification_period, listener)
        
    if verbose:
        
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
    
    sample_rate = file_.get_sample_rate()
    
    return clips, sample_rate
        
        
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
    
        
def _sample_clips(clips, settings):
    
    train_size = settings.training_set_size
    
    if train_size is None:
        return clips
    
    else:
        # training set size specified

        val_size = settings.validation_set_size
        test_size = settings.test_set_size
        
        n = train_size + val_size + test_size
        
        if n < len(clips):
            indices = frozenset(random.sample(range(len(clips)), n))
            clips = [c for i, c in enumerate(clips) if i in indices]
        
        return clips
        
        
def _compute_features(clips, sample_rate, settings):
    
    waveforms = _get_waveforms(clips)
    
    num_examples = len(clips)
    print_if_verbose = ConditionalPrinter(settings.verbose)
    
    print_if_verbose('Trimming waveforms...')
    waveforms = _trim_waveforms(waveforms, sample_rate, settings)
    
    print_if_verbose('Computing spectrograms...')
    start_time = time.time()
    spectrograms = _compute_spectrograms(waveforms, sample_rate, settings)
    elapsed_time = time.time() - start_time
    
    spectrogram_rate = num_examples / elapsed_time
    spectrum_rate = spectrogram_rate * spectrograms[0].shape[0]
    print_if_verbose((
        'Computed {} spectrograms of shape {} in {:.1f} seconds, an '
        'average of {:.1f} spectrograms and {:.1f} spectra per '
        'second.').format(
            num_examples, spectrograms[0].shape, elapsed_time,
            spectrogram_rate, spectrum_rate))
    
    print_if_verbose('Trimming spectrogram frequencies...')
    print_if_verbose('    input shape {}'.format(spectrograms.shape))
    spectrograms = _trim_spectrograms(spectrograms, sample_rate, settings)
    print_if_verbose('    output shape {}'.format(spectrograms.shape))
    
    print_if_verbose('Clipping spectrogram powers...')
    power_clipping_range = _clip_spectrogram_powers(spectrograms, settings)
    print_if_verbose('    {}'.format(power_clipping_range))
    
    print_if_verbose('Normalizing spectrograms...')
    normalization = _normalize_spectrograms(spectrograms, settings)
    print_if_verbose('    {}'.format(normalization))
    print_if_verbose('    {} {}'.format(spectrograms.mean(), spectrograms.std()))
    
    print_if_verbose('Flattening spectrograms...')
    features = spectrograms.reshape((num_examples, -1))
    
    return features
    

def _get_waveforms(clips):
    num_clips = len(clips)
    num_samples = len(clips[0].waveform)
    waveforms = np.zeros((num_clips, num_samples))
    for i, clip in enumerate(clips):
        waveforms[i] = clip.waveform
    return waveforms
        
        
def _trim_waveforms(waveforms, sample_rate, settings):
    start_index = signal_utils.seconds_to_frames(
        settings.waveform_start_time, sample_rate)
    duration = signal_utils.seconds_to_frames(
        settings.waveform_duration, sample_rate)
    end_index = start_index + duration
    return waveforms[:, start_index:end_index]
    
    
def _compute_spectrograms(waveforms, sample_rate, settings):
    
    num_examples = len(waveforms)
    print_if_verbose = ConditionalPrinter(settings.verbose)
    
    window_size = signal_utils.seconds_to_frames(
        settings.spectrogram_window_size, sample_rate)
    hop_size = signal_utils.seconds_to_frames(
        settings.spectrogram_hop_size, sample_rate)
    dft_size = tfa_utils.get_dft_size(window_size)
    
    params = Settings(
        window=data_windows.create_window('Hann', window_size),
        hop_size=hop_size,
        dft_size=dft_size,
        ref_power=1)

    num_spectra, num_bins = _get_spectrogram_shape(waveforms, params)

    spectrograms = np.zeros(
        (num_examples, num_spectra, num_bins), dtype='float32')
    
    for i in range(num_examples):
        if i != 0 and i % 10000 == 0:
            print_if_verbose('    {}...'.format(i))
        waveform = waveforms[i, :]
        spectrogram = _compute_spectrogram(waveform, params)
        spectrograms[i, :, :] = spectrogram
        
    return spectrograms
    
    
def _get_spectrogram_shape(waveforms, params):
    spectrogram = _compute_spectrogram(waveforms[0], params)
    return spectrogram.shape


def _compute_spectrogram(waveform, params):
    gram = tfa_utils.compute_spectrogram(
        waveform,
        params.window.samples,
        params.hop_size,
        params.dft_size)
    return tfa_utils.linear_to_log(gram, 1)

    
def _trim_spectrograms(spectrograms, sample_rate, params):
    num_bins = spectrograms.shape[2]
    start_index = _freq_to_bin_num(
        params.spectrogram_start_freq, sample_rate, num_bins)
    end_index = _freq_to_bin_num(
        params.spectrogram_end_freq, sample_rate, num_bins) + 1
    return spectrograms[:, :, start_index:end_index]


def _freq_to_bin_num(freq, sample_rate, num_bins):
    bin_size = (sample_rate / 2) / (num_bins - 1)
    return int(round(freq / bin_size))


def _clip_spectrogram_powers(spectrograms, settings):
    
    """
    Clips powers on the tails of the specified spectrograms' combined
    histogram.
    
    This function clips the values of spectrogram bins whose that lie
    on the lower and upper tails of the spectrograms' combined histogram.
    The clipping limits are chosen to eliminate from the histogram the
    largest number of bins from each tail whose value sum to half of the
    fraction `settings.spectrogram_power_clipping_fraction` of the
    histogram's total sum.
    """
    
    if settings.spectrogram_power_clipping_fraction != 0:
        
        histogram, edges = np.histogram(spectrograms, bins=1000)
        f = settings.spectrogram_power_clipping_fraction / 2
        t = f * np.sum(histogram)
            
        s = 0
        i = 0
        while s + histogram[i] <= t:
            i += 1
            
        s = 0
        j = len(histogram)
        while s + histogram[j - 1] <= t:
            j -= 1
    
        min_power = edges[i]
        max_power = edges[j]
                
#         import matplotlib.pyplot as plt
#         limits = (edges[0], edges[-1])
#         plt.figure(1)
#         plt.plot(edges[:-1], histogram)
#         plt.axvline(min_power, color='r')
#         plt.axvline(max_power, color='r')
#         plt.xlim(limits)
        
        spectrograms[spectrograms < min_power] = min_power
        spectrograms[spectrograms > max_power] = max_power
        
#         histogram, edges = np.histogram(spectrograms, range=limits, bins=1000)
#         plt.figure(2)
#         plt.plot(edges[:-1], histogram)
#         plt.xlim(limits)
#            
#         plt.show()
    
        return min_power, max_power
    
    else:
        return None
    
    
def _normalize_spectrograms(spectrograms, settings):
    
    """Normalizes spectrograms to have zero mean and unit variance."""
    
    if settings.normalize_spectrograms:
        
        # Subtract mean.
        mean = spectrograms.mean()
        spectrograms -= mean
        
        # Divide by standard deviation.
        std = spectrograms.std()
        spectrograms /= std
        
        return mean, std
    
    else:
        return None
    
    
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
    permutation = np.random.permutation(num_examples)
    features = features[permutation]
    targets = targets[permutation]
    
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


def _train_classifier(train_set, settings):
    
    input_length = train_set.features.shape[1]
    model = _create_classifier_model(input_length, settings)
    
    verbose = 2 if settings.verbose else 0

    model.fit(
        train_set.features,
        train_set.targets,
        epochs=settings.num_epochs,
        batch_size=settings.batch_size,
        verbose=verbose)
    
    return model
    
       
def _create_classifier_model(input_length, settings):
    
    layer_sizes = settings.hidden_layer_sizes + [1]
    num_layers = len(layer_sizes)
    
    regularizer = keras.regularizers.l2(settings.regularization_beta)
    
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


def _show_stats(train_stats, val_stats):
    
    import matplotlib.pyplot as plt
    
    plt.plot(
        train_stats.false_positive_rate, train_stats.true_positive_rate, 'b',
        val_stats.false_positive_rate, val_stats.true_positive_rate, 'g')
    
    plt.legend(['Training', 'Validation'])
    
    plt.xlim((0, 1))
    plt.ylim((0, 1))
    
    plt.show()
        
        
if __name__ == '__main__':
    _main()
    