import numpy as np

from vesper.util.batch_iterator import BatchIterator
from vesper.util.bunch import Bunch
from vesper.tests.test_case import TestCase


class BatchIteratorTests(TestCase):


    def test_iteration(self):
        for num_examples in range(1, 11):
            for batch_size in range(1, num_examples + 1):
                self._test_iteration(num_examples, batch_size)
        
        
    def _test_iteration(self, num_examples, batch_size):
        
        data_set = _create_data_set(num_examples)
        num_batches = num_examples // batch_size
        received = np.zeros(num_examples)
        
        batch_iterator = BatchIterator(data_set, batch_size)
        self.assertIs(batch_iterator.data_set, data_set)
        self.assertEquals(batch_iterator.batch_size, batch_size)
        self.assertEquals(batch_iterator.num_batches, num_batches)
        
        batch_num = 0
        
        for features, targets in batch_iterator:
            
            # Check batch size.
            self.assertEqual(len(features), batch_size)
            self.assertEqual(len(targets), batch_size)
            
            # Check that features and targets match.
            for f, t in zip(features, targets):
                self.assertEqual(f[0], t)
                
            for t in targets:
                received[t] = 1
            
            batch_num += 1
            self.assertEqual(batch_iterator.num_batches_completed, batch_num)
                        
        self.assertEqual(batch_num, num_batches)
        
        # Check that each received example was received exactly once.
        self.assertEqual(sum(received), num_batches * batch_size)
        
            
            
def _create_data_set(num_examples):
    indices = np.arange(num_examples)
    offsets = 1000 * np.arange(2)
    features = offsets + indices.reshape((num_examples, 1))
    return Bunch(features=features, targets=indices)
