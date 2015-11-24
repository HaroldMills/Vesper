"""
Trains an NFC coarse classifier.

The classifier classifies a clip by first classifying a sequence of short,
regularly spaced segments within the clip using a *segment classifier*.
Each segment is classified by the segment classifier as either a call
segment or some other kind of segment. The entire clip is then classified
as a call if and only if one or more of the segments was classified as a
call segment.

The segment classifier used by a coarse classifier is an SVM that is
trained on segments that come from two archives, one containing call clips
and the other containing noise clips. The call segments used for training
are extracted from clips of the call archive that are classified as "Call"
clips (including clips that are classified to "Call" subclasses) and that
have nonempty selections. One training segment is extracted from each such
clip whose selection is of sufficient duration. The location of the
extracted segment within the selection is chosen at random using a
uniform distribution.

The noise segments used for training are extracted from clips of the
noise archive that are classified as "Noise" clips. One noise segment
is extracted from the center 100 ms of each such clip. The location
of the extracted segment within the center 100 ms is chosen at random
using a uniform distribution.

The directories of the call and noise archives are currently hard-coded.

The script performs n-fold cross-validation segment and call classifier
training when the value of the `num_cross_validation_folds` configuration
parameter (see the `_CONFIGS` dictionary below) is positive
(cross-validation is disabled if the value is zero). Cross-validation
results are written to a file named:

    <detector> Classifier Training and Test Results.csv
    
where <detector> is either "Tseep" or "Thrush". The file is located in
the same directory as the call and noise archives.

The script takes one command line argument, which must be either
"Tseep" or "Thrush", indicating the detector for which a classifier
is to be created. It writes the constructed classifier object to a
pickle file named:

    <detector> Coarse Classifier.pkl
    
where <detector> is either "Tseep" or "Thrush".

The classifier is of Python class `NfcCoarseClassifier`, and can be
loaded via the `create_classifier` function of the `nfc_coarse_classifier`
module.
"""


from __future__ import print_function
import cPickle as pickle
import os.path
import random
import sys

from sklearn import cross_validation
from sklearn import svm
import numpy as np

from vesper.archive.archive import Archive
from vesper.util.bunch import Bunch
from vesper.util.nfc_coarse_classifier import NfcCoarseClassifier
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier
import vesper.util.data_windows as data_windows


'''
Kinds of training/test clip splits I'd like to work with:

Training and test clips from same query:
    Select clips by station(s), year(s), season(s).
    Create n folds.
    
Training and test clips from different queries:
    Select training clips.
    Select test clips.
'''


# _TEST_CASES = '''
# 
# defaults:
#     stations: FSR
#     years: 2012, 2013, 2014
#     seasons: Spring, Fall
#     
# cases:
# 
#     - name: Train/test FSR
#       
#     - name: Train/test F
#       clips:
#           stations: F
#           
#     - name: Train F, test SR
#       training_clips:
#           stations: F
#       test_clips:
#           stations: SR
#       
#     - name: Train FSR 2014, Test FSR 2012-2013
#       training_clips:
#           stations: FSR
#           years: 2014
#       test_clips:
#           stations: FSR
#           years: 2012, 2013
#   
# '''


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CALL_ARCHIVE_NAME = 'MPG Ranch 2012-2014'
_NOISE_ARCHIVE_NAME_PREFIX = 'MPG Ranch Sampled 2014 '


_CONFIGS = {
            
    'Tseep': Bunch(
        detector_name = 'Tseep',
        segment_duration = .03,
        segment_hop_size = .015,
        noise_segment_source_duration = .1,
        num_cross_validation_folds=10,
        num_learning_curve_points=10,
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=4000,
        max_freq=10000,
        min_power=-10,
        max_power=65,
        pooling_block_size=(2, 2),
        include_norm_in_features=False,
        svc_params={
            'cache_size': 500,
            'kernel': 'rbf',
            'gamma': .001,
            'C': 1000.
        }),
            
    'Thrush': Bunch(
        detector_name = 'Thrush',
        segment_duration = .09,
        segment_hop_size = .045,
        noise_segment_source_duration = .2,
        num_cross_validation_folds=10,
        num_learning_curve_points=10,
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
        include_norm_in_features=False,
        svc_params={
            'cache_size': 500,
            'kernel': 'rbf',
            'gamma': .001,
            'C': 1000.
        })
            
}


def _main():
    
    # Seed random number generators so that script yields identical
    # results on repeated runs.
    random.seed(0)
    np.random.seed(0)
    
    config = _CONFIGS[sys.argv[1]]
    
    print('Getting clips from archives...')
    clips = _get_clips_from_archives(config)
    print('Got {} clips.\n'.format(len(clips)))
    
    print('Extracting clip segments...')
    clips = _extract_clip_segments(clips, config)
    print('Extracted segments from {} clips.\n'.format(len(clips)))
    
#     print('Balancing numbers of call and noise clips...')
#     clips = _balance_clips(clips)
#     print(
#         'Now have {} clips, half calls and half noises.\n'.format(len(clips)))
    
    # Perform cross-validation training on clip folds.
    if config.num_cross_validation_folds != 0:
        results = _train_and_test_cross_validation_classifiers(clips, config)
        _save_training_and_test_results(results, config)
    
    print('Training segment classifier on all clips...')
    segment_classifier = _train_segment_classifier(clips, config)
    print()

    _save_clip_classifier(config, segment_classifier)

    
def _balance_clips(clips):
    
    calls = []
    noises = []
    
    for clip in clips:
        if clip.clip_class_name == 'Noise':
            noises.append(clip)
        else:
            calls.append(clip)
            
    num_calls = len(calls)
    num_noises = len(noises)
    
    if num_calls < num_noises:
        noises = list(np.random.choice(noises, num_calls, replace=False))
    elif num_noises < num_calls:
        calls = list(np.random.choice(calls, num_noises, replace=False))
        
    assert(len(calls) == len(noises))
    
    return calls + noises

            
def _get_clips_from_archives(config):
    call_clips = _get_clips_from_archive(_CALL_ARCHIVE_NAME, 'Call*', config)
    noise_archive_name = _NOISE_ARCHIVE_NAME_PREFIX + config.detector_name
    noise_clips = _get_clips_from_archive(noise_archive_name, 'Noise', config)
    return call_clips + noise_clips
    

def _get_clips_from_archive(archive_name, clip_class_name, config):
    archive_dir_path = _create_full_path(archive_name)
    archive = Archive(archive_dir_path)
    archive.open()
    clips = archive.get_clips(
        clip_class_name=clip_class_name, detector_name=config.detector_name)
    archive.close()
    return clips


def _create_full_path(*parts):
    return os.path.join(_DIR_PATH, *parts)


def _extract_clip_segments(clips, config):
    return [clip for clip in clips if _extract_clip_segment(clip, config)]


def _extract_clip_segment(clip, config):
    
    ncc = nfc_coarse_classifier
    duration = config.segment_duration

    if clip.clip_class_name == 'Noise':
        segment = ncc.extract_clip_segment(
            clip, duration, ncc.SEGMENT_SOURCE_CLIP_CENTER,
            config.noise_segment_source_duration)

    else:
        segment = ncc.extract_clip_segment(
            clip, duration, ncc.SEGMENT_SOURCE_SELECTION)
        
    if segment is not None:
        segment.name = os.path.basename(clip.file_path)
        segment.clip_class_name = clip.clip_class_name
        clip.segment = segment

    return segment is not None


def _train_and_test_cross_validation_classifiers(clips, config):
    
    # TODO: Support training and test queries that limit stations,
    # years, and seasons. Support training and test splits that use
    # different queries.
    
    n = config.num_learning_curve_points
    fractions = (1. + np.arange(n)) / n
    # fractions = fractions[:1]
    results = []
      
    for fold_num, all_training_clips, test_clips in \
            _generate_clip_folds(clips, config.num_cross_validation_folds):
            
        print((
            'Training classifiers for cross-validation fold {} of '
            '{}...\n').format(fold_num, config.num_cross_validation_folds))
        
        for fraction in fractions:
              
            percent = _fraction_to_percent(fraction)
            print((
                'Training classifier with {} percent of training '
                'clips...').format(percent))
            
            training_clips = _sample_items(all_training_clips, fraction)
        
            _, segment_training_results, segment_test_results, \
            _, clip_training_results, clip_test_results = \
                _train_clip_classifier(training_clips, test_clips, config)
                
            _show_results(
                segment_training_results, segment_test_results,
                clip_training_results, clip_test_results)
            
            training_counts = _count_clips(training_clips)
            test_counts = _count_clips(test_clips)
            results.append(
                (fold_num, percent) + training_counts +
                segment_training_results + clip_training_results +
                test_counts + segment_test_results + clip_test_results)
            
            print()
          
    return results
    
    
def _generate_clip_folds(clips, num_folds):
    
    targets = _get_targets(clips)

    # Make `clips` a NumPy array so we can do fancy indexing to create folds.
    clips = np.array(clips)
    
    fold_num = 1
    
    for training_indices, test_indices in cross_validation.StratifiedKFold(
            targets, n_folds=num_folds, shuffle=True, random_state=0):
        
        yield (fold_num, clips[training_indices], clips[test_indices])
    
        fold_num += 1
        
        
def _get_targets(items):
    return np.array([_get_target(item.clip_class_name) for item in items])


def _get_target(clip_class_name):
    if clip_class_name == 'Noise':
        return 0
    elif clip_class_name.startswith('Call'):
        return 1
    else:
        raise ValueError(
            'Unrecognized clip class "{}".'.format(clip_class_name))


def _fraction_to_percent(fraction):
    return int(round(100 * fraction))
  
  
def _sample_items(items, fraction):
    n = int(round(fraction * len(items)))
    # np.random.seed(0)
    return np.random.choice(items, n, replace=False)
          
  
def _train_clip_classifier(training_clips, test_clips, config):
    
    segment_classifier = _train_segment_classifier(training_clips, config)
        
    segment_training_results = _test_segment_classifier(
        segment_classifier, training_clips, config)
    
    segment_test_results = _test_segment_classifier(
        segment_classifier, test_clips, config)
        
    clip_classifier = NfcCoarseClassifier(config, segment_classifier)
    
    clip_training_results = _test_clip_classifier(
        clip_classifier, training_clips, config)
    
    clip_test_results = _test_clip_classifier(
        clip_classifier, test_clips, config)
    
    return (
        segment_classifier, segment_training_results, segment_test_results,
        clip_classifier, clip_training_results, clip_test_results)


def _train_segment_classifier(training_clips, config):
    features, targets = _get_segment_features_and_targets(
        training_clips, config)
    classifier = svm.SVC(**config.svc_params)
    classifier.fit(features, targets)
    return classifier
    
    
def _get_segment_features_and_targets(clips, config):
    segments = _get_clip_segments(clips)
    features = _get_segment_features(segments, config)
    targets = _get_targets(segments)
    return (features, targets)


def _get_clip_segments(clips):
    return [clip.segment for clip in clips]


def _get_segment_features(segments, config):
    get_features = nfc_coarse_classifier.get_segment_features
    return [get_features(segment, config)[0] for segment in segments]


def _test_segment_classifier(classifier, test_clips, config):
    features, targets = _get_segment_features_and_targets(test_clips, config)
    predictions = classifier.predict(features)
    return _tally_classification_results(targets, predictions)


def _tally_classification_results(targets, predictions):
    num_true_positives = ((targets == 1) & (predictions == 1)).sum()
    num_false_negatives = ((targets == 1) & (predictions == 0)).sum()
    num_false_positives = ((targets == 0) & (predictions == 1)).sum()
    num_true_negatives = ((targets == 0) & (predictions == 0)).sum()
    return (
        num_true_positives, num_false_negatives, num_false_positives,
        num_true_negatives)
        

def _test_clip_classifier(classifier, clips, config):
    targets = _get_targets(clips)
    predict = classifier.classify_clip
    predictions = np.array([predict(clip) for clip in clips])
    return _tally_classification_results(targets, predictions)


def _show_results(
        segment_training_results, segment_test_results,
        clip_training_results, clip_test_results):
    
    _show_results_aux('segment training', segment_training_results)
    _show_results_aux('segment test', segment_test_results)
    _show_results_aux('clip training', clip_training_results)
    _show_results_aux('clip test', clip_test_results)
    
    
def _show_results_aux(name, results):
    print(name, results, _get_result_percents(*results))


def _get_result_percents(tp, fn, fp, tn):
    p = float(tp + fn)
    n = float(fp + tn)
    fractions = (tp / p, fn / p, fp / n, tn / n)
    percents = [_fraction_to_percent_2(f) for f in fractions]
    return tuple(percents)
    
    
def _fraction_to_percent_2(x):
    # Round percent to nearest tenth.
    return round(x * 1000) / 10


def _count_clips(clips):
    num_clips = len(clips)
    targets = _get_targets(clips)
    num_calls = targets[targets == 1].sum()
    num_noises = num_clips - num_calls
    return (num_clips, num_calls, num_noises)


_COLUMN_NAMES = '''
Fold
Training Percent
Training Clips
Training Calls
Training Noises
Training Segment True Positives
Training Segment False Negatives
Training Segment False Positives
Training Segment True Negatives
Training Clip True Positives
Training Clip False Negatives
Training Clip False Positives
Training Clip True Negatives
Test Clips
Test Calls
Test Noises
Test Segment True Positives
Test Segment False Negatives
Test Segment False Positives
Test Segment True Negatives
Test Clip True Positives
Test Clip False Negatives
Test Clip False Positives
Test Clip True Negatives
'''


def _save_training_and_test_results(results, config):
    
    name_format = '{} Classifier Results.csv'
    file_name = name_format.format(config.detector_name)
    file_path = _create_full_path(file_name)
    
    print(
        'Saving training and test results to file "{}".'.format(file_path))

    header_line = _create_csv_header(_COLUMN_NAMES)
    result_lines = [_create_csv_result_line(r) for r in results]
    lines = [header_line] + result_lines
    text = ''.join([line + '\n' for line in lines])
    
    with open(file_path, 'w') as file_:
        file_.write(text)
        
    print()
    


def _create_csv_header(column_names):
    names = column_names.strip().split('\n')
    names = [name.strip() for name in names]
    return ','.join(names)


def _create_csv_result_line(results):
    result_strings = [str(r) for r in results]
    return ','.join(result_strings)


def _save_clip_classifier(config, segment_classifier):
    
    clip_classifier = NfcCoarseClassifier(config, segment_classifier)
    
    file_name = '{} Coarse Classifier.pkl'.format(config.detector_name)
    file_path = _create_full_path(file_name)
    
    print('Saving clip classifier to file "{}".'.format(file_path))
    
    with open(file_path, 'wb') as file_:
        pickle.dump(clip_classifier, file_)
        
    print()
        
        
if __name__ == '__main__':
    _main()
