"""
Creates a call/noise clip segment classifier for the specified detector.

The name of the detector (e.g. "Tseep" or "Thrush") is specified as the
single command-line argument to this script. Given labeled examples of
call and noise segments, the script trains a classifier to distinguish
the two types of segments. Training is performed on increasingly large
subsets of the examples, using stratified k-fold cross-validation for
each subset. The correct test classification rate is reported for each
fold, along with the mean for all folds. At the end of all of the
cross-validation training runs learning curve data are output in the
form of a table giving the size of each subset of examples on which
cross-validation training was performed and the mean correct test
classification rate for the classifiers that were built from those
examples. Finally, a classifier is trained on all of the examples.

The script requires two HDF5 input files with names:

    <detector> Call Segments.hdf5
    <detector> Noise Segments.hdf5
    
for example:

    Tseep Call Segments.hdf5
    Tseep Noise Segments.hdf5
    
and writes the final classifier to a pickle file called:

    <detector> Segment Classifier.pkl
    
for example:

    Tseep Segment Classifier.pkl
    
The classifier is a scikit-learn Support Vector classifier and can be read
by a Python script with:

    with open(pickle_file_path, 'r') as file_:
        classifier = pickle.load(file_)
        
See http://scikit-learn.org/stable/modules/model_persistence.html for more
on scikit-learn classifier persistance.
"""


from __future__ import print_function
import cPickle as pickle
import os.path
import sys

from sklearn import cross_validation
from sklearn import svm
import h5py
import numpy as np

from vesper.util.bunch import Bunch
import vesper.util.call_noise_classifier as call_noise_classifier
import vesper.util.data_windows as data_windows


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'


_CONFIGS = {
                       
    'Tseep': Bunch(
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=4000,
        max_freq=11000,
        min_power=-10,
        max_power=65,
        pooling_block_size=(2, 2),
        svc_params={
            'gamma': .001,
            'C': 1000.
        }),
        
    'Thrush': Bunch(
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=1500,
        max_freq=4000,
        min_power=-10,
        max_power=65,
        pooling_block_size=(2, 2),
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
    
    detector_name = sys.argv[1]
    
    all_segments = _load_segments(detector_name)
    
    config = _CONFIGS[detector_name]
    
    num_fractions = 10
    fractions = (1. + np.arange(num_fractions)) / num_fractions
    mean_scores = np.zeros_like(fractions)
    
    print()
    
    for i, fraction in enumerate(fractions):
        
        percent = _fraction_to_percent(fraction)
        print((
            'Training cross-validation classifiers with {} percent of '
            'examples...').format(percent))
        
        segments = _sample_segments(all_segments, fraction)
        fold_scores = _train_cross_validation_classifiers(segments, config)
        mean_scores[i] = fold_scores.mean()
        
        _show_fold_scores(fold_scores)
        print()
        
    _show_learning_curve(fractions, mean_scores)
        
    print('Training final classifier with all examples...')
    classifier = _train_final_classifier(segments, config)
    
    _save_classifier(classifier, detector_name)
    
    
def _load_segments(detector_name):
    
    path = _create_input_file_path(detector_name, 'Call')
    print('Loading example call segments from "{}"...'.format(path))
    call_segments = _load_segments_file(path)
    print('Loaded {} call segments.'.format(len(call_segments)))
    
    path = _create_input_file_path(detector_name, 'Noise')
    print('Loading example noise segments from "{}"...'.format(path))
    noise_segments = _load_segments_file(path)
    print('Loaded {} noise segments.'.format(len(noise_segments)))
    
    return call_segments + noise_segments


def _create_input_file_path(detector_name, classification):
    file_name = '{} {} Segments.hdf5'.format(detector_name, classification)
    return _create_file_path(file_name)


def _create_file_path(file_name):
    return os.path.join(_DIR_PATH, file_name)


def _load_segments_file(file_path):
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


def _fraction_to_percent(fraction):
    return int(round(100 * fraction))


def _sample_segments(segments, fraction):
    n = int(round(fraction * len(segments)))
    np.random.seed(0)
    return np.random.choice(segments, n, replace=False)
        

def _train_cross_validation_classifiers(segments, config):
    
    dataset = _create_dataset(segments, config)
    X = dataset.features
    y = dataset.targets
    
    folds = cross_validation.StratifiedKFold(
        y, n_folds=10, shuffle=True, random_state=0)
    
    fold_scores = np.array(
        [_train_and_test_classifier(X, y, f, config) for f in folds])
    
    return fold_scores


def _create_dataset(segments, config):
    
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
    features, spectra, _ = call_noise_classifier.get_segment_features(
        segment, config)
    target = _TARGETS[segment.classification.split('.')[0]]
    return (features, target, segment.name, spectra)
     

def _train_and_test_classifier(X, y, fold, config):
    
    train_indices, test_indices = fold
    
    X_train = X[train_indices]
    y_train = y[train_indices]
    
    X_test = X[test_indices]
    y_test = y[test_indices]
        
    classifier = _train_classifier(X_train, y_train, config)
    
    predictions = classifier.predict(X_test)
    num_errors = np.abs(predictions - y_test).sum()
    num_predictions = len(predictions)
    score = (num_predictions - num_errors) / float(num_predictions)
    
    return score

    
def _train_classifier(X, y, config):
    classifier = svm.SVC(**config.svc_params)
    classifier.fit(X, y)
    return classifier

   
def _show_fold_scores(scores):
    f = _format_score
    s = ' '.join([f(score) for score in scores])
    print('    fold scores', s)
    print('    mean fold score', f(scores.mean()))

def _format_score(score):
    return '{:.1f}'.format(100 * score)


def _show_learning_curve(fractions, mean_scores):
    print('Learning curve:')
    for i in xrange(len(mean_scores)):
        percent = _fraction_to_percent(fractions[i])
        print('    ', percent, _format_score(mean_scores[i]))
    print()
        
       
def _train_final_classifier(segments, config):
    dataset = _create_dataset(segments, config)
    X = dataset.features
    y = dataset.targets
    return _train_classifier(X, y, config)

 
def _save_classifier(classifier, detector_name):
    file_path = _create_output_file_path(detector_name)
    print('Writing final classifier to "{}"...'.format(file_path))
    with open(file_path, 'wb') as file_:
        pickle.dump(classifier, file_)
    
    
def _create_output_file_path(detector_name):
    file_name = '{} Segment Classifier.pkl'.format(detector_name)
    return _create_file_path(file_name)


if __name__ == '__main__':
    _main()
