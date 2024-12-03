The models of this classifier have the same structure and parameter
values as the corresponding models of the MPG Ranch NFC Coarse
Classifier 4.0. The only difference is that the models of this
classifier are stored in Keras model HDF5 files instead of as TensorFlow
saved models. The Keras model HDF5 files were created from the saved
models by the `patch_hdf5_model_from_saved_model.py` script. See that
script for details.

As of 2024-12-02, the MPG Ranch NFC classifier versions 4.1 and the
detector versions 1.1 (which are built around the 4.1 classifiers)
work with TensorFlow 2.12 but not with the most recent TensorFlow
version 2.18 (or 2.16.2, the last version that supports Intel Macs).
The issue is that more recent versions of TensorFlow can no longer
read the `Keras Model.h5` model files of the classifiers. I spent
some time looking into this issue, and it appears to be fixable.
See directory
`Desktop/NFC/Vesper Project/2024-12 TensorFlow Model HDF5 File Updates`
on my laptop for details. I have decided to defer fixing this issue
until I move detection out of the Vesper Server, sticking with
TensorFlow 2.12 for now.
