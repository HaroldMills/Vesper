"""Module containing class `BatchIterator`"""


import numpy as np


class BatchIterator:
    
    """Iterator that yields batches of machine learning examples."""
    
    
    def __init__(self, data_set, batch_size):
        
        self._data_set = data_set
        self._batch_size = batch_size
        
        num_examples = len(self._data_set.features)
        
        self._permutation = np.random.permutation(num_examples)

        self._num_batches = num_examples // batch_size
        self._num_batches_completed = 0
        
        
    
    @property
    def data_set(self):
        return self._data_set
    

    @property
    def batch_size(self):
        return self._batch_size
    
    
    @property
    def num_batches(self):
        return self._num_batches
    
    
    @property
    def num_batches_completed(self):
        return self._num_batches_completed
    
    
    def __iter__(self):
        return self
    
    
    def __next__(self):
        
        if self._num_batches_completed == self._num_batches:
            raise StopIteration
        
        else:
            
            start_index = self._num_batches_completed * self._batch_size
            end_index = start_index + self._batch_size
            indices = self._permutation[start_index:end_index]
            
            data_set = self._data_set
            features = data_set.features[indices]
            targets = data_set.targets[indices]
            
            self._num_batches_completed += 1
            
            return (features, targets)


    def get_next_batch(self):
        return self.__next__()
    