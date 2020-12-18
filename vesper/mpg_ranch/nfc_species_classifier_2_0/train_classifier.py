"""
Script that trains a tseep species classifier.

To use tensorboard during or after model training, open a terminal and say:

    conda activate vesper-dev-tf2
    tensorboard --logdir "/Users/Harold/Desktop/NFC/Data/Vesper ML/
        MPG Ranch Species Classifier 2.0/Logs/Tseep"
        
and then visit:

    127.0.0.1:6006
    
in Chrome.
"""


import time

from tensorflow.keras.layers import (
    BatchNormalization, Conv2D, Dense, Flatten, MaxPooling2D)
# from tensorflow.keras.layers import Dropout
from tensorflow.keras.models import Sequential
import tensorflow as tf

from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_species_classifier_2_0.classifier_utils \
    as classifier_utils
import vesper.mpg_ranch.nfc_species_classifier_2_0.dataset_utils \
    as dataset_utils
import vesper.util.yaml_utils as yaml_utils


'''
NFC species classifier input requirements:

1. Clip duration must be 600 ms.

2. Clip must contain a call.

3. Call must start at most 400 ms from start of clip.


Classification processing:

1. Compute spectrogram and normalize background.

2. Apply neural network to spectrogram, yielding a vector of species scores.
   Each score is in [0, 1] and the scores sum to one.

3. If the maximum species score is above a threshold, classify the clip
   as that species. Otherwise leave clip unclassified.
   
   
Training data augmentations:

* Place call start uniformly in [0, 400].

* Shift spectrogram up or down along frequency axis? (But might this
  confuse classes?)

* Stretch along time and/or frequency axis by resampling? (But might this
  confuse classes?)
   
   
Notes:

* I considered designing the classifier to work with clips of varying
durations, say between 200 ms and 600 ms. This would allow the classifier
to be used with clips shorter than 600 ms, like those from the Old Bird
detectors, when the recordings from which the clips were extracted are
not available. Developing such a classifier would be more complicated,
though, than developing one that works with a fixed-size input. I'm
inclined to try to solve a relatively simple classification problem
first, and then consider trying to solve more complicated ones if that
effort succeeds. I am also interested in experimenting with learned
background normalization, which will be simpler if input clips are of
a fixed duration.
'''


TSEEP_SETTINGS = Settings(
    
    clip_type='Tseep',
    
    class_count=dataset_utils.CLASS_COUNT,
    
    waveform_sample_rate=24000,
    
    # Call start time settings. During training, waveforms are sliced so
    # that call start times are uniformly distributed in the interval
    # from `waveform_slice_min_call_start_time` to
    # `waveform_slice_max_call_start_time`. Set the min and max start
    # times equal to make all calls start at a particular time.
    # waveform_slice_min_call_start_time=.200,
    # waveform_slice_max_call_start_time=.200,
    waveform_slice_min_call_start_time=.000,
    waveform_slice_max_call_start_time=.400,
    
    waveform_slice_duration=.600,
    
    # `True` if and only if the waveform amplitude scaling data
    # augmentation is enabled. This augmentation scales each waveform
    # randomly to distribute the waveform log RMS amplitudes uniformly
    # within a roughly 48 dB window.
    waveform_amplitude_scaling_data_augmentation_enabled=False,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=20,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=4000,
    spectrogram_end_freq=10500,
    
    # The maximum spectrogram frequency shift for data augmentation,
    # in bins. Set this to zero to disable this augmentation.
    max_spectrogram_frequency_shift=0,
    
    spectrogram_background_normalization_percentile_rank=40,
    
    # training settings
    training_batch_size=128,
    training_epoch_step_count=12,  # epoch size is batch size times step count
    training_epoch_count=100,
    model_save_period=5,           # epochs
    dropout_rate=.3,
    
    # validation settings
    validation_batch_size=1,
    validation_step_count=1000,
    
)


def main():
    
    settings = TSEEP_SETTINGS
    
    train_annotator(settings)

    # show_waveform_dataset_examples('Training', settings)
    
    # show_sliced_waveform_dataset_examples('Training', settings)
    
    # show_training_dataset_examples('Training', settings)
    
    # show_dataset_sizes(settings)
    
    
def train_annotator(settings):
      
    s = settings
      
    training_name = classifier_utils.create_training_name(s)
      
    training_dataset = get_dataset('Training', s).batch(s.training_batch_size)
    validation_dataset = \
        get_dataset('Validation', s).batch(s.validation_batch_size)
      
    input_shape = dataset_utils.get_spectrogram_slice_shape(settings)
    
    print('input_shape', input_shape)
      
    model = Sequential([
          
        Conv2D(32, (5, 5), activation='relu', input_shape=input_shape),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        # MaxPooling2D((2, 2)),
          
        # Conv2D(16, (1, 1), activation='relu'),
        # BatchNormalization(),
   
        Conv2D(32, (5, 5), activation='relu'),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        # MaxPooling2D((2, 2)),
          
        Conv2D(32, (5, 5), activation='relu'),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        MaxPooling2D((2, 2)),
          
        Conv2D(16, (1, 1), activation='relu'),
        BatchNormalization(),
  
        Conv2D(32, (40, 12), activation='relu'),
        BatchNormalization(),
        MaxPooling2D((2, 1)),
 
        Conv2D(16, (1, 1), activation='relu'),
        BatchNormalization(),
  
        Flatten(),
          
        # Dense(32, activation='relu'),
        # BatchNormalization(),
          
        Dense(32, activation='relu'),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
          
        Dense(s.class_count, activation='softmax')
          
    ])
      
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy'])
      
    model.summary()
      
    log_dir_path = classifier_utils.get_training_log_dir_path(training_name)
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=str(log_dir_path), histogram_freq=1)
      
    model_save_callback = ModelSaveCallback(training_name, settings)
       
    model.fit(
        training_dataset, epochs=s.training_epoch_count,
        steps_per_epoch=s.training_epoch_step_count, verbose=2,
        validation_data=validation_dataset,
        validation_steps=s.validation_step_count,
        callbacks=[tensorboard_callback, model_save_callback])


# def train_annotator(settings):
#       
#     s = settings
#       
#     training_name = classifier_utils.create_training_name(s)
#       
#     training_dataset = get_dataset('Training', s).batch(s.training_batch_size)
#     validation_dataset = \
#         get_dataset('Validation', s).batch(s.validation_batch_size)
#       
#     input_shape = dataset_utils.get_spectrogram_slice_shape(settings)
#       
#     model = Sequential([
#           
#         Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
#         # Dropout(s.dropout_rate),
#         BatchNormalization(),
#         # MaxPooling2D((2, 2)),
#           
#         # Conv2D(16, (1, 1), activation='relu'),
#         # BatchNormalization(),
#    
#         Conv2D(32, (3, 3), activation='relu'),
#         # Dropout(s.dropout_rate),
#         BatchNormalization(),
#         # MaxPooling2D((2, 2)),
#           
#         Conv2D(32, (3, 3), activation='relu'),
#         # Dropout(s.dropout_rate),
#         BatchNormalization(),
#         MaxPooling2D((2, 2)),
#           
#         Conv2D(16, (1, 1), activation='relu'),
#         BatchNormalization(),
#   
#         Conv2D(32, (100, 15), activation='relu'),
#         BatchNormalization(),
#         MaxPooling2D((2, 1)),
#  
#         Conv2D(16, (1, 1), activation='relu'),
#         BatchNormalization(),
#   
#         Flatten(),
#           
#         # Dense(32, activation='relu'),
#         # BatchNormalization(),
#           
#         Dense(32, activation='relu'),
#         # Dropout(s.dropout_rate),
#         BatchNormalization(),
#           
#         Dense(s.class_count, activation='softmax')
#           
#     ])
#       
#     model.compile(
#         optimizer='adam',
#         loss='categorical_crossentropy',
#         metrics=['accuracy'])
#       
#     model.summary()
#       
#     log_dir_path = classifier_utils.get_training_log_dir_path(training_name)
#     tensorboard_callback = tf.keras.callbacks.TensorBoard(
#         log_dir=log_dir_path, histogram_freq=1)
#       
#     model_save_callback = ModelSaveCallback(training_name, settings)
#        
#     model.fit(
#         training_dataset, epochs=s.training_epoch_count,
#         steps_per_epoch=s.training_epoch_step_count, verbose=2,
#         validation_data=validation_dataset,
#         validation_steps=s.validation_step_count,
#         callbacks=[tensorboard_callback, model_save_callback])
       
  
class ModelSaveCallback(tf.keras.callbacks.Callback):
      
      
    def __init__(self, training_name, settings):
        self._training_name = training_name
        self._settings = settings
          
          
    def on_epoch_end(self, epoch, logs=None):
          
        epoch_num = epoch + 1
          
        if epoch_num % self._settings.model_save_period == 0:
              
            model_dir_path = \
                classifier_utils.get_tensorflow_saved_model_dir_path(
                    self._training_name, epoch_num)
                  
            # Create model directory if needed.
            model_dir_path.mkdir(parents=True, exist_ok=True)
            
            # Save model in TensorFlow SavedModel format.
            self.model.save(str(model_dir_path), save_format='tf')
              
            save_training_settings(self._settings, self._training_name)
              
            print(f'Saved model at end of epoch {epoch_num}.')
              
         
def get_dataset(name, settings):
    dir_path = classifier_utils.get_dataset_dir_path(settings.clip_type, name)
    return dataset_utils.create_training_dataset(dir_path, settings)
 
 
def save_training_settings(settings, training_name):
    file_path = classifier_utils.get_training_settings_file_path(training_name)
    text = yaml_utils.dump(settings.__dict__, default_flow_style=False)
    file_path.write_text(text)


def show_waveform_dataset_examples(dataset_name, settings):
    
    dir_path = classifier_utils.get_dataset_dir_path(
        settings.clip_type, dataset_name)
    
    dataset = dataset_utils.create_waveform_dataset_from_tfrecord_files(
        dir_path)
    
    start_time = time.time()
    
    n = 10
    
    for waveform, call_start_index, label, one_hot_label, clip_id \
            in dataset.take(n):
        
        sample_rate = settings.waveform_sample_rate
        waveform_duration = len(waveform) / sample_rate
        call_start_time = call_start_index.numpy() / sample_rate
        label = label.numpy()
        one_hot_label = one_hot_label.numpy()
        clip_id = clip_id.numpy()

        print(
            waveform_duration, call_start_time, label, one_hot_label, clip_id)
        
    end_time = time.time()
    delta_time = end_time - start_time
    print(f'{n / delta_time} clips per second.')
    
    
def show_sliced_waveform_dataset_examples(dataset_name, settings):
    
    dir_path = classifier_utils.get_dataset_dir_path(
        settings.clip_type, dataset_name)
    
    dataset = dataset_utils.create_training_dataset(dir_path, settings)
    
    start_time = time.time()
    
    n = 10
    
    for waveform, call_start_index, label, one_hot_label, clip_id in \
            dataset.take(n):
        
        sample_rate = settings.waveform_sample_rate
        waveform_duration = len(waveform) / sample_rate
        call_start_time = call_start_index.numpy() / sample_rate
        label = label.numpy()
        one_hot_label = one_hot_label.numpy()
        clip_id = clip_id.numpy()
        
        print(
            waveform_duration, call_start_time, label, one_hot_label, clip_id)

    end_time = time.time()
    delta_time = end_time - start_time
    print(f'{n / delta_time} clips per second.')


# def show_training_dataset_examples(dataset_name, settings):
#     
#     dir_path = classifier_utils.get_dataset_dir_path(
#         settings.clip_type, dataset_name)
#     
#     dataset = dataset_utils.create_training_dataset(dir_path, settings)
#     
#     start_time = time.time()
#     
#     n = 10
#     
#     for spectrogram, call_start_index, label, one_hot_label, clip_id in \
#             dataset.take(n):
#         
#         sample_rate = settings.waveform_sample_rate
#         shape = tf.shape(spectrogram).numpy()
#         call_start_time = call_start_index.numpy() / sample_rate
#         label = label.numpy()
#         one_hot_label = one_hot_label.numpy()
#         clip_id = clip_id.numpy()
#         
#         print(shape, call_start_time, label, one_hot_label, clip_id)
# 
#     end_time = time.time()
#     delta_time = end_time - start_time
#     print(f'{n / delta_time} clips per second.')
    
    
def show_training_dataset_examples(dataset_name, settings):
    
    dir_path = classifier_utils.get_dataset_dir_path(
        settings.clip_type, dataset_name)
    
    dataset = dataset_utils.create_training_dataset(dir_path, settings)
    
    start_time = time.time()
    
    n = 10
    
    for spectrogram, one_hot_label in dataset.take(n):
        
        shape = tf.shape(spectrogram).numpy()
        one_hot_label = one_hot_label.numpy()
        
        print(shape, one_hot_label)

    end_time = time.time()
    delta_time = end_time - start_time
    print(f'{n / delta_time} clips per second.')
    
    
def show_dataset_sizes(settings):
    
    from tensorflow.data import TFRecordDataset
    
    for dataset_name in ('Training', 'Validation'):
        
        total_size = 0
        
        print(f'Sizes of files in dataset "{dataset_name}":')
        
        dir_path = classifier_utils.get_dataset_dir_path(
            settings.clip_type, dataset_name)
        
        file_paths = sorted(dir_path.glob('*.tfrecords'))
        
        for file_path in file_paths:
            dataset = TFRecordDataset([str(file_path)])
            size = 0
            for _ in dataset:
                size += 1
            print(f'    {file_path.name}: {size}')
            total_size += size
        
        print(f'Total size of dataset "{dataset_name}": {total_size}')


if __name__ == '__main__':
    main()
