import sys

import numpy as np

from vesper.util.binary_classification_stats import BinaryClassificationStats
from vesper.tests.test_case import TestCase


_STAT_NAMES = (

    'num_true_positives',
    'num_false_negatives',
    'num_true_negatives',
    'num_false_positives',
    
    'num_examples',
    'num_positive_examples',
    'num_negative_examples',
    
    'num_positives',
    'num_negatives',
    
    'num_correct',
    'num_incorrect',
    
    'true_positive_rate',
    'false_negative_rate',
    'true_negative_rate',
    'false_positive_rate',
    
    'accuracy',
    'precision',
    'recall',
    'f1_score'
    
)


_TARGETS = np.array([1, 1, 1, 0, 0, 0, 0, 0])

_VALUES = np.array([.9, .6, .4, .9, .6, 0, 0, 0])

_TEST_CASES = [
    
    (.5, (
        
        2,  # num true positives
        1,  # num false negatives
        3,  # num true negatives
        2,  # num false positives
        
        8,  # num examples
        3,  # num positive examples
        5,  # num_negative examples
        
        4,  # num positives
        4,  # num negatives
        
        5,  # num correct
        3,  # num incorrect
        
        2 / 3,  # true positive rate
        1 / 3,  # false negative rate
        .6,     # true negative rate
        .4,     # false positive rate
        
        .625,   # accuracy
        .5,     # precision
        2 / 3,  # recall
        
    )),
         
    (.7, (
        
        1,  # num true positives
        2,  # num false negatives
        4,  # num true negatives
        1,  # num false positives
        
        8,  # num examples
        3,  # num positive examples
        5,  # num_negative examples
        
        2,  # num positives
        6,  # num negatives
        
        5,  # num correct
        3,  # num incorrect
        
        1 / 3,  # true positive rate
        2 / 3,  # false negative rate
        .8,     # true negative rate
        .2,     # false positive rate
        
        .625,   # accuracy
        .5,     # precision
        1 / 3,  # recall
        
    )),
         
]
  
      
class BinaryClassificationStatsTests(TestCase):


    def test_scalar_threshold(self):
                 
        for threshold, expected_stats in _TEST_CASES:
             
            s = BinaryClassificationStats(_TARGETS, _VALUES, threshold)
             
            for name, expected in zip(_STAT_NAMES, expected_stats):
                 
                actual = getattr(s, name)
                 
                try:
                    self.assertAlmostEqual(actual, expected)
                     
                except AssertionError:
                    print((
                        'Scalar test failed for threshold {}, statistic '
                        '"{}".').format(threshold, name), file=sys.stderr)
                    raise
                
                
    def test_array_threshold(self):
        
        thresholds = np.array([t for t, _ in _TEST_CASES])
        expected_stats = np.array([list(s) for _, s in _TEST_CASES]).T
        
        s = BinaryClassificationStats(_TARGETS, _VALUES, thresholds)
        
        for name, expected in zip(_STAT_NAMES, expected_stats):
            
            actual = getattr(s, name)
            
            try:
                self.assert_arrays_close(actual, expected)
                
            except AssertionError:
                print(
                    'Array test failed for statistic "{}".'.format(
                        name), file=sys.stderr)
