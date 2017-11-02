"""Module containing class `BinaryClassificationStats`."""


import numpy as np


class BinaryClassificationStats:
    
    """
    Binary classification statistics.
    
    A `BinaryClassificationStats` instance has attributes providing
    various statistics pertinent to binary classification problems.
    Each statistic is either scalar or vector valued, according to
    whether the instance was initialized with a scalar or vector
    `threshold` value, respectively.
    """
    
    
    def __init__(self, targets, values, threshold=.5):
        
        if np.isscalar(threshold):
            stats = self._compute_stats(targets, values, threshold)
            
        else:
            stats = np.array([
                self._compute_stats(targets, values, t)
                for t in threshold]).T
        
        self._threshold, self._tp, self._fn, self._tn, self._fp = stats
        
        
    def _compute_stats(self, targets, values, threshold):
        
        predictions = (values >= threshold).astype('float')
        
        def count(target, prediction):
            return np.sum(np.logical_and(
                targets == target, predictions == prediction))
            
        tp = count(1, 1)
        fn = count(1, 0)
        tn = count(0, 0)
        fp = count(0, 1)
        
        return [threshold, tp, fn, tn, fp]
        
        
    @property
    def threshold(self):
        return self._threshold
    
    
    @property
    def num_true_positives(self):
        return self._tp
    
    
    @property
    def num_false_negatives(self):
        return self._fn
    
    
    @property
    def num_true_negatives(self):
        return self._tn
    
    
    @property
    def num_false_positives(self):
        return self._fp
    
    
    @property
    def num_examples(self):
        return self.num_positive_examples + self.num_negative_examples
    
    
    @property
    def num_positive_examples(self):
        return self.num_true_positives + self.num_false_negatives
    
    
    @property
    def num_negative_examples(self):
        return self.num_true_negatives + self.num_false_positives
    
    
    @property
    def num_positives(self):
        return self.num_true_positives + self.num_false_positives
    
    
    @property
    def num_negatives(self):
        return self.num_true_negatives + self.num_false_negatives
    
    
    @property
    def num_correct(self):
        return self.num_true_positives + self.num_true_negatives
    
    
    @property
    def num_incorrect(self):
        return self.num_false_positives + self.num_false_negatives
    
    
    @property
    def true_positive_rate(self):
        return self.num_true_positives / self.num_positive_examples
    
    
    @property
    def true_negative_rate(self):
        return self.num_true_negatives / self.num_negative_examples
    
    
    @property
    def false_positive_rate(self):
        return 1 - self.true_negative_rate
    
    
    @property
    def false_negative_rate(self):
        return 1 - self.true_positive_rate
    
    
    @property
    def accuracy(self):
        return self.num_correct / self.num_examples
    
    
    @property
    def precision(self):
        return self.num_true_positives / self.num_positives
    
    
    @property
    def recall(self):
        return self.true_positive_rate
