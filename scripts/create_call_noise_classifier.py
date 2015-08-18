from __future__ import print_function
import os.path
import sys

from sklearn import cross_validation
from sklearn import svm
import h5py
import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.spectrogram import Spectrogram
import vesper.util.data_windows as data_windows


def _create_input_file_path(detector_name):
    dir_path = '/Users/Harold/Desktop/NFC/Data/MPG Ranch'
    file_name = '{:s} Call Noise Segments.hdf5'.format(detector_name)
    return os.path.join(dir_path, file_name)


_CONFIGS = {
                       
    'Tseep': Bunch(
        input_file_path=_create_input_file_path('Tseep'),
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=4000,
        max_freq=11000,
        min_power=-10,
        max_power=65,
        svc_params={
            'gamma': .001,
            'C': 1000.
        }),
        
    'Thrush': Bunch(
        input_file_path=_create_input_file_path('Thrush'),
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=1500,
        max_freq=4000,
        min_power=-10,
        max_power=65,
        svc_params={
            'gamma': .001,
            'C': 1000.
        })

}


_TARGETS = {
    'Noise': 0,
    'Call': 1
}


def _main():
    
    # _test_sum_adjacent()
    
    config = _CONFIGS[sys.argv[1]]
    
    segments = _load_segments(config.input_file_path)
    
    num_fractions = 10
    fractions = (1. + np.arange(num_fractions)) / num_fractions
    average_scores = np.zeros_like(fractions)
    
    for i, fraction in enumerate(fractions):
        
        print('creating dataset...')
        dataset = _create_dataset(segments, fraction, config)
        
        print('training and testing classifiers...')
        X = dataset.features
        y = dataset.targets
        folds = cross_validation.StratifiedKFold(
            y, n_folds=10, shuffle=True, random_state=0)
        scores = np.array(
            [_train_and_test_classifier(X, y, f, config) for f in folds])
        average_score = scores.mean()
        
        print('scores', scores)
        print('average scrore {:f}'.format(average_score))
        print
        
        average_scores[i] = average_score
        
    for i in xrange(len(average_scores)):
        percentage = int(round(fractions[i] * 100))
        print(percentage, average_scores[i])
    
    
def _train_and_test_classifier(X, y, fold, config):
    
    train_indices, test_indices = fold
    
    X_train = X[train_indices]
    y_train = y[train_indices]
    
    X_test = X[test_indices]
    y_test = y[test_indices]
        
    classifier = svm.SVC(**config.svc_params)
    classifier.fit(X_train, y_train)
    
    predictions = classifier.predict(X_test)
    num_errors = np.abs(predictions - y_test).sum()
    num_predictions = len(predictions)
    score = (num_predictions - num_errors) / float(num_predictions)
    
    return score

    
def _load_segments(file_path):
    with h5py.File(file_path, 'r') as file_:
        segments = [_create_segment(file_[name]) for name in file_]
    return segments
    
    
def _create_segment(dataset):

    # Note that within this function, `dataset` is an HDF5 dataset
    # and not a scikit-learn dataset.
    
    samples = dataset[:]
    
    attrs = dataset.attrs
    sample_rate = attrs['sample_rate']
    classification = attrs['classification']
    
    segment = Bunch(
        name=dataset.name,
        samples=samples,
        sample_rate=sample_rate,
        classification=classification)
    
    return segment


def _create_dataset(segments, fraction, config):
    
    n = int(round(fraction * len(segments)))
    np.random.seed(0)
    segments = np.random.choice(segments, n, replace=False)
    
    tuples = [_create_segment_tuple(s, config) for s in segments]
    
    features, targets, names, images = zip(*tuples)
    features = np.array(features)
    targets = np.array(targets)
    
    dataset = Bunch(
        features=features,
        targets=targets,
        names=names,
        images=images)
    
    return dataset
    
    
def _create_segment_tuple(segment, config):
    features, spectra = _create_features(segment, config)
    target = _TARGETS[segment.classification]
    return (features, target, segment.name, spectra)
     

def _create_features(segment, config):
    
    c = config
    
    spectrogram = Spectrogram(segment, c.spectrogram_params)
    spectra = spectrogram.spectra
    
    # Clip spectra to specified power range.
    spectra.clip(config.min_power, config.max_power)
    
    # Remove portions of spectra outside of specified frequency range.
    sample_rate = segment.sample_rate
    dft_size = c.spectrogram_params.dft_size
    start_index = _freq_to_index(c.min_freq, sample_rate, dft_size)
    end_index = _freq_to_index(c.max_freq, sample_rate, dft_size) + 1
    spectra = spectra[:, start_index:end_index]
    
    # TODO: Should summing happen before logs are taken?
    # TODO: Consider parameterizing both the block size and the method
    # of combining spectrogram values (e.g. is sum or max better?).
    spectra = _sum_adjacent(spectra, 2, 2)
    
    features = _normalize(spectra.flatten())
    
    return (features, spectra)


def _freq_to_index(freq, sample_rate, dft_size):
    bin_size = sample_rate / dft_size
    return int(round(freq / bin_size))


def _sum_adjacent(x, m, n):
    
    xm, xn = x.shape
    
    xm = (xm // m) * m
    xn = (xn // n) * n
    x = x[:xm, :xn]
    
    # Sum columns.
    x.shape = (xm, xn / n, n)
    x = x.sum(2)
    xn /= n
    
    # Sum rows.
    x = x.transpose()
    x.shape = (xn, xm / m, m)
    x = x.sum(2)
    x = x.transpose()
    
    return x
    
    
def _test_sum_adjacent():
    x = np.arange(24)
    x.shape = (4, 6)
    print(x)
    x = _sum_adjacent(x, 2, 3)
    print(x)
    
    
def _normalize(x):
    norm = np.linalg.norm(x)
    return x / norm if norm != 0 else x


if __name__ == '__main__':
    _main()
