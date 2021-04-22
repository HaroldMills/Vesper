The models of this classifier have the same structure and parameter
values as the corresponding models of the MPG Ranch NFC Coarse
Classifier 4.0. The only difference is that the models of this
classifier are stored in Keras model HDF5 files instead of as TensorFlow
saved models. The Keras model HDF5 files were created from the saved
models by the `patch_hdf5_model_from_saved_model.py` script. See that
script for details.
