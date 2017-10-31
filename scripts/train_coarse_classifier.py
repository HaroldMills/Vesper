from pathlib import Path
import time

from keras.models import Sequential
from keras.layers import Dense
import h5py
import keras
import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.settings import Settings
from vesper.util.spectrogram import Spectrogram
import vesper.util.data_windows as data_windows
import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


_FILE_PATH = Path('/Users/Harold/Desktop/clips.hdf5')


_SETTINGS = {
     
    'Tseep': Settings(
        
        detector_name='Tseep',
        
        waveform_start_time=.080,
        waveform_duration=.150,
        
        spectrogram_params=Settings(
            window=data_windows.create_window('Hann', 64),
            hop_size=32,
            dft_size=64,
            ref_power=1),
                      
        spectrogram_start_freq=2000,
        spectrogram_end_freq=10000,
        
        spectrogram_power_clipping_fraction=.001,
        normalize_spectrograms=True,
        
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
        
    )
             
#     'Tseep': Bunch(
#         detector_name = 'Tseep',
#         spectrogram_params=Bunch(
#             window=data_windows.create_window('Hann', 256),
#             hop_size=128,
#             dft_size=256,
#             ref_power=1),
#         validation_set_size = 5000,
#         test_set_size = 5000
#     )
             
}


# TODO: Get from HDF5 file? Or make independent and resample clips as needed?
_SAMPLE_RATE = 22050


def _main():
    
    settings = _SETTINGS['Tseep']
    
    print('Reading data set...')
    waveforms, classifications = _read_data_set()
    
    num_clips = waveforms.shape[0]
    num_calls = int(np.sum(classifications))
    num_noises = num_clips - num_calls
    
    print(
        'Read {} clips, {} calls and {} noises.'.format(
            num_clips, num_calls, num_noises))
    
    print('Trimming waveforms...')
    waveforms = _trim_waveforms(waveforms, settings)
    
    print('Computing spectrograms...')
    start_time = time.time()
    spectrograms = _compute_spectrograms(waveforms, settings)
    elapsed_time = time.time() - start_time
    
    spectrogram_rate = num_clips / elapsed_time
    spectrum_rate = spectrogram_rate * spectrograms[0].shape[0]
    print((
        'Computed {} spectrograms of shape {} in {:.1f} seconds, an average '
        'of {:.1f} spectrograms and {:.1f} spectra per second.').format(
            num_clips, spectrograms[0].shape, elapsed_time, spectrogram_rate,
            spectrum_rate))
    
    print('Trimming spectrogram frequencies...')
    print('    input shape {}'.format(spectrograms.shape))
    spectrograms = _trim_spectrograms(spectrograms, settings)
    print('    output shape {}'.format(spectrograms.shape))
    
    print('Clipping spectrogram powers...')
    power_clipping_range = _clip_spectrogram_powers(spectrograms, settings)
    print('    {}'.format(power_clipping_range))
    
    print('Normalizing spectrograms...')
    normalization = _normalize_spectrograms(spectrograms, settings)
    print('    {}'.format(normalization))
    print('    {} {}'.format(spectrograms.mean(), spectrograms.std()))
    
    print('Creating data sets...')
    train_set, val_set, _ = \
        _create_data_sets(spectrograms, classifications, settings)
        
    print('Training classifier...')
    model = _train_classifier(train_set, settings)
       
    print('Testing classifier...')
    _test_classifier(model, train_set, 'training')
    _test_classifier(model, val_set, 'validation')

    print()
        

def _create_data_sets(spectrograms, classifications, settings):
    
    num_examples, num_spectra, num_bins = spectrograms.shape
    
    assert(len(classifications) == num_examples)
    
    # Shuffle examples.
    permutation = np.random.permutation(num_examples)
    spectrograms = spectrograms[permutation]
    classifications = classifications[permutation]
    
    # Flatten spectrograms to make features.
    features = spectrograms.reshape((num_examples, num_spectra * num_bins))
    
    # Targets are just classifications, each in {0, 1}.
    targets = classifications
    
    val_size = settings.validation_set_size
    test_size = settings.test_set_size
    test_start = num_examples - test_size
    val_start = test_start - val_size
    
    train_set = Bunch(
        features=features[:val_start],
        targets=targets[:val_start])
    
    val_set = Bunch(
        features=features[val_start:test_start],
        targets=targets[val_start:test_start])
    
    test_set = Bunch(
        features=features[test_start:],
        targets=targets[test_start:])
    
    return train_set, val_set, test_set
    
    
def _read_data_set():
    
    with h5py.File(_FILE_PATH) as f:
        waveforms = f['samples'][...]
        classifications = f['classifications'][...]
        
    return waveforms, classifications
    
        
def _trim_waveforms(waveforms, settings):
    start_index = signal_utils.seconds_to_frames(
        settings.waveform_start_time, _SAMPLE_RATE)
    duration = signal_utils.seconds_to_frames(
        settings.waveform_duration, _SAMPLE_RATE)
    end_index = start_index + duration
    return waveforms[:, start_index:end_index]
    
    
def _compute_spectrograms(waveforms, settings):
    
    params = settings.spectrogram_params
    
    num_clips = waveforms.shape[0]
    num_spectra, num_bins = _get_spectrogram_shape(waveforms, params)

    spectrograms = np.zeros(
        (num_clips, num_spectra, num_bins), dtype='float32')
    
    for i in range(num_clips):
        if i != 0 and i % 10000 == 0:
            print('    {}...'.format(i))
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

    
def _compute_spectrogram_less_quickly(waveform, params):
    sound = Bunch(samples=waveform, sample_rate=_SAMPLE_RATE)
    spectrogram = Spectrogram(sound, params)
    return spectrogram.spectra
    
    
def _trim_spectrograms(spectrograms, params):
    num_bins = spectrograms.shape[2]
    start_index = _freq_to_bin_num(
        params.spectrogram_start_freq, _SAMPLE_RATE, num_bins)
    end_index = _freq_to_bin_num(
        params.spectrogram_end_freq, _SAMPLE_RATE, num_bins) + 1
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
    
    
def _train_classifier(train_set, settings):
    
    input_length = train_set.features.shape[1]
    model = _create_classifier_model(input_length, settings)

    model.fit(
        train_set.features,
        train_set.targets,
        epochs=settings.num_epochs,
        batch_size=settings.batch_size,
        verbose=2)
    
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
        
    
def _test_classifier(model, data_set, data_set_name=None):
     
    features = data_set.features
    targets = data_set.targets
     
    activations = model.predict(features, batch_size=len(features))
     
    accuracy, precision, recall = _compute_statistics(targets, activations)
     
    if data_set_name is not None:
        print(
            '{} accuracy, precision, and recall: {:.3f} {:.3f} {:.3f}'.format(
                data_set_name, accuracy, precision, recall))
     
    return accuracy, precision, recall


def _compute_statistics(targets, activations, threshold=.5):
    
    predictions = (activations >= threshold).astype('float')
    
    accuracy = np.sum(predictions == targets) / len(targets)
    
    num_true_positives = np.sum(np.logical_and(targets == 1, predictions == 1))
    num_positives = np.sum(predictions)
    num_calls = np.sum(targets)
    
    precision = num_true_positives / num_positives
    recall = num_true_positives / num_calls
    
    return accuracy, precision, recall


if __name__ == '__main__':
    _main()
    