import numpy as np

import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator_utils \
    as annotator_utils
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.dataset_utils \
    as dataset_utils


class Inferrer:
    
    
    def __init__(self, start_model_info, end_model_info=None):
        
        self._start_model, self._start_settings = \
            annotator_utils.load_model_and_settings(*start_model_info)
        
        if end_model_info is None:
            self._end_model = self._start_model
            self._end_settings = self._start_settings
        else:
            self._end_model, self._end_settings = \
                annotator_utils.load_model_and_settings(*end_model_info)
    
    
    @property
    def sample_rate(self):
        return self._start_settings.waveform_sample_rate
    
    
    def get_call_bounds(self, waveform_dataset):
        
        dataset = dataset_utils.create_inference_dataset(
            waveform_dataset, self._start_settings)
        
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
            
            start_index = self._get_call_bound_index(
                self._start_model, self._start_settings, gram_slices)
            return self._gram_index_to_waveform_index(start_index)
    
    
    def _get_call_bound_index(self, model, settings, gram_slices):
        
        scores = model.predict(gram_slices).flatten()
        
        if settings.bound_type == 'Start':
            offset = settings.call_start_index_offset
        else:
            offset = settings.call_end_index_offset
            
        return np.argmax(scores) + offset
    
    
    def _gram_index_to_waveform_index(self, gram_index):
        
        s = self._start_settings
        
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
            
            end_index = self._get_call_bound_index(
                self._end_model, self._end_settings, gram_slices)
            
            # Recover spectrogram length from slices shape.
            shape = gram_slices.shape
            slice_count = shape[0]
            slice_length = shape[1]
            gram_length = slice_count + slice_length - 1
            
            # Complement end index to account for backward order of slices
            # and spectra within them.
            end_index = gram_length - 1 - end_index
            
            return self._gram_index_to_waveform_index(end_index)
