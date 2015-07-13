from __future__ import print_function

from sklearn import cross_validation
from sklearn import svm
import h5py
import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.spectrogram import Spectrogram
import vesper.util.data_windows as data_windows


_INPUT_FILE_PATH = \
    '/Users/Harold/Desktop/NFC/Data/MPG Ranch/CallNoiseSegments.hdf5'
    
_WINDOW_TYPE = 'Hann'
_WINDOW_SIZE = 110
_HOP_SIZE = 55
_DFT_SIZE = 128
_MIN_FREQ = 4000
_MAX_FREQ = 11000
_MIN_POWER = -10
_MAX_POWER = 65
    
_WINDOW = data_windows.create_window(_WINDOW_TYPE, _WINDOW_SIZE)
_SPECTROGRAM_PARAMS = Bunch(
    window=_WINDOW,
    hop_size=_HOP_SIZE,
    dft_size=_DFT_SIZE,
    ref_power=1)

_TARGETS = {
    'Noise': 0,
    'Call': 1
}


def _main():
    
    # _test_sum_adjacent()
    
    print('creating dataset...')
    segments = _create_dataset()
    
    print('training and testing classifiers...')
    X = segments.features
    y = segments.targets
    folds = cross_validation.StratifiedKFold(
        y, n_folds=10, shuffle=True, random_state=0)
    scores = np.array([_train_and_test_classifier(X, y, f) for f in folds])
    
    print('scores', scores)
    print('average scrore {:f}'.format(scores.mean()))
    
    
def _train_and_test_classifier(X, y, fold):
    
    train_indices, test_indices = fold
    
    X_train = X[train_indices]
    y_train = y[train_indices]
    
    X_test = X[test_indices]
    y_test = y[test_indices]
        
    classifier = svm.SVC(gamma=.001, C=100.)
    classifier.fit(X_train, y_train)
    
    predictions = classifier.predict(X_test)
    num_errors = np.abs(predictions - y_test).sum()
    num_predictions = len(predictions)
    score = (num_predictions - num_errors) / float(num_predictions)
    
    return score

    
def _create_dataset():
    segments = _load_segments(_INPUT_FILE_PATH)
    dataset = _create_dataset_from_segments(segments)
    return dataset
    
    
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


def _create_dataset_from_segments(segments):
    
    tuples = [_create_segment_tuple(s) for s in segments]
    features, targets, names, images = zip(*tuples)
    features = np.array(features)
    targets = np.array(targets)
    
    dataset = Bunch(
        features=features,
        targets=targets,
        names=names,
        images=images)
    
    return dataset
    
    
def _create_segment_tuple(segment):
    features, spectra = _create_features(segment)
    target = _TARGETS[segment.classification]
    return (features, target, segment.name, spectra)
     

def _create_features(segment):
    
    spectrogram = Spectrogram(segment, _SPECTROGRAM_PARAMS)
    spectra = spectrogram.spectra
    
    # Clip spectra to specified power range.
    spectra.clip(_MIN_POWER, _MAX_POWER)
    
    # Remove portions of spectra outside of specified frequency range.
    sample_rate = segment.sample_rate
    start_index = _freq_to_index(_MIN_FREQ, sample_rate, _DFT_SIZE)
    end_index = _freq_to_index(_MAX_FREQ, sample_rate, _DFT_SIZE) + 1
    spectra = spectra[:, start_index:end_index]
    
    # TODO: Should summing happen before logs are taken?
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
