from tensorflow.data import Dataset
import numpy as np


def main():
    
    dataset_count = 10
    
    def create_dataset(i):
        return Dataset.range(4 * i, 4 * (i + 1))
    
    dataset = Dataset.range(dataset_count).map(create_dataset)
    
    for d in dataset:
        show_dataset(d)
        
    d = dataset.flat_map(lambda x: x)
    show_dataset(d)
    
    d = dataset.interleave(lambda x: x, cycle_length=2, block_length=3)
    show_dataset(d)
    
    # Repeat two datasets of different lengths and interleave them.
    a = Dataset.from_tensor_slices(np.arange(10)).repeat()
    b = Dataset.from_tensor_slices(100 + np.arange(17)).repeat()
    datasets = [a, b]
    n = len(datasets)
    c = Dataset.from_tensor_slices(datasets)
    d = c.interleave(lambda x: x, cycle_length=n).take(50)
    show_dataset(d)
    
    
def show_dataset(dataset):
    elements = list(dataset.as_numpy_iterator())
    print(elements)
    
    
def compose_datasets(datasets):
    n = len(datasets)
    return Dataset.range(n).map(lambda i: datasets[i])


if __name__ == '__main__':
    main()
