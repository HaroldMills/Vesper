"""
Script that patches a Keras HDF5 model file with parameter values
obtained from a TensorFlow saved model.

When I trained the neural networks for the MPG Ranch NFC Coarse Classifier
versions 3.0 and 4.0, I inadvertently saved untrained parameter values to
a Keras HDF5 model file instead of trained parameter values. The trained
values were only saved as a TensorFlow saved model. This script patches
the Keras HDF5 model file with trained parameter values read from the
saved model. The script reads the parameter values directly from one of
the saved model files since that's the only way I could figure out how to
get at the saved model parameter values. The saved model did not appear
to be usable as is with TensorFlow 2, perhaps because it was written
using too old a version of TensorFlow 1.

I guessed at the structure of the saved model files, knowing the sizes
and types of the tensors that were supposed to be in them, and also
from the contents of their `variables.index` files as displayed in a
text editor, and fortunately my guess seems to have been correct.
TensorFlow 2 detectors and classifiers constructed from the patched
HDF5 model files perform the same as TensorFlow 1 detectors and
classifiers constructed from the saved model files. 

I used this script to patch model files for versions 3.1 and 4.1 of the
MPG Ranch NFC Coarse Classifier. For each of the four classifier models,
(i.e. Tseep and Thrush for each classifier version), I copied the
relevant model directory from the 3.0 or 4.0 version to the 3.1 or 4.1
version, modified the `CLIP_TYPE` and `CLASSIFIER_VERSION` attributes
of this script (see below) accordingly, and then ran the script. After
running the script I deleted the saved models, since they did not
appear to be usable with TensorFlow 2.
"""


from pathlib import Path

import h5py
import numpy as np


CLIP_TYPE = 'Thrush'
CLASSIFIER_VERSION = '4_1'

CLASSIFIER_DIR_PATH = Path(
    f'/Users/harold/Documents/Code/Python/Vesper/vesper/mpg_ranch/'
    f'nfc_coarse_classifier_{CLASSIFIER_VERSION}/{CLIP_TYPE} Classifier')

VARIABLES_DIR_PATH = \
    CLASSIFIER_DIR_PATH / 'TensorFlow SavedModel' / 'variables'

TF_DATA_FILE_PATH = VARIABLES_DIR_PATH / 'variables.data-00000-of-00001'

HDF5_FILE_PATH = CLASSIFIER_DIR_PATH / 'Keras Model.h5'


def main():
    
    floats, global_step = read_tf_data_file(TF_DATA_FILE_PATH)
    
    print(f'global_step: {global_step}')
    
    start_index = 0
    
    with h5py.File(HDF5_FILE_PATH, 'r+') as f:
        
        weight_group = f['/model_weights']
        
        for layer_name in weight_group.keys():
            
            if layer_name != 'flatten' and \
                    not layer_name.startswith('max_pooling'):
                
                layer_group = weight_group[f'{layer_name}/{layer_name}']
                
                for dataset_name, dataset in layer_group.items():
                    
                    print(
                        layer_name, dataset_name, dataset.shape, dataset.size)
                    
                    end_index = start_index + dataset.size
                    
                    x = floats[start_index:end_index]
                    x.shape = dataset.shape
                    dataset[:] = x
                    
                    start_index = end_index
    
    if start_index != len(floats):
        print(
            f'Warning: number of saved model floats processed {start_index} '
            f'was less than total number {len(floats)}.')


def read_tf_data_file(path):
    with open(path, 'rb') as data_file:
        buffer = data_file.read()
    floats = np.frombuffer(buffer[:-8], 'float32')
    global_step = np.frombuffer(buffer[-8:], 'int64')[0]
    return floats, global_step


if __name__ == '__main__':
    main()
