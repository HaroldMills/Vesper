import logging

import numpy as np
import tensorflow as tf

from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator_utils \
    as annotator_utils
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.dataset_utils \
    as dataset_utils
import vesper.util.yaml_utils as yaml_utils


_MODEL_NAMES = {
    'Tseep': '2020-07-06_09.33.54',
    # 'Tseep': '2020-07-03_15.00.57',
    # 'Tseep': '2020-07-02_18.09.08',
    # 'Tseep': '2020-07-02_18.01.56',
    # 'Tseep': '2020-07-02_17.47.55',
    # 'Tseep': '2020-07-02_17.38.18',
    # 'Tseep': '2020-07-02_15.05.08',
    # 'Tseep': '2020-07-02_14.58.08',
    # 'Tseep': '2020-07-02_14.46.36',
    # 'Tseep': 'start_2020-06-23_15.10.16',
}


class Inferrer:
    
    
    def __init__(self, clip_type, model_name=None):
        self.clip_type = clip_type
        self._model = _load_model(clip_type, model_name)
        self._settings = _load_settings(clip_type, model_name)
    
    
    @property
    def sample_rate(self):
        return self._settings.waveform_sample_rate
    
    
    def get_call_bounds(self, waveform_dataset):
        
        dataset = dataset_utils.create_inference_dataset(
            waveform_dataset, self._settings)
        
        return tuple(
            self._get_call_bounds(*element) for element in dataset)
    
    
    def _get_call_bounds(
            self, forward_gram_slices, backward_gram_slices, *args):
        
        bounds = (
            self._get_call_start_index(forward_gram_slices),
            self._get_call_end_index(backward_gram_slices))
        
        return bounds + tuple(args)
        
        
    def _get_call_start_index(self, gram_slices):
        
        if len(gram_slices) == 0:
            # no gram slices
            
            return None
        
        else:
            # at least one gram slice
            
            start_index = self._get_call_bound_index(gram_slices)
            return self._gram_index_to_waveform_index(start_index)
    
    
    def _get_call_bound_index(self, gram_slices):
        scores = self._model.predict(gram_slices).flatten()
        return np.argmax(scores) + self._settings.call_bound_index_offset
    
    
    def _gram_index_to_waveform_index(self, gram_index):
        
        s = self._settings
        
        # Get center time of window from which spectrum was computed.
        window_size = s.spectrogram_window_size
        hop_size = window_size * s.spectrogram_hop_size / 100
        time = gram_index * hop_size + window_size / 2
        
        # Get index of waveform sample closest to center time.
        waveform_index = int(round(time * s.waveform_sample_rate))
        
        return waveform_index
    
        
    def _get_call_end_index(self, gram_slices):
        
        if len(gram_slices) == 0:
            # no gram slices
            
            return None
        
        else:
            # at least one gram slice
            
            end_index = self._get_call_bound_index(gram_slices)
            
            # Recover spectrogram length from slices shape.
            shape = gram_slices.shape
            slice_count = shape[0]
            slice_length = shape[1]
            gram_length = slice_count + slice_length - 1
            
            # Complement end index to account for backward order of slices
            # and spectra within them.
            end_index = gram_length - 1 - end_index
            
            return self._gram_index_to_waveform_index(end_index)


def _load_model(clip_type, model_name):
    if model_name is None:
        model_name = _MODEL_NAMES[clip_type]
    dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        clip_type, model_name)
    logging.info(
        'Loading annotator model from "{}"...'.format(dir_path))
    model = tf.keras.models.load_model(dir_path)
    return model
    
    
def _load_settings(clip_type, model_name):
    if model_name is None:
        model_name = _MODEL_NAMES[clip_type]
    file_path = annotator_utils.get_model_settings_file_path(
        clip_type, model_name)
    logging.info(
        'Loading annotator settings from "{}"...'.format(file_path))
    text = file_path.read_text()
    settings_dict = yaml_utils.load(text)
    settings = Settings.create_from_dict(settings_dict)
    return settings
