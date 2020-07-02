"""
Module containing NFC bounding interval annotator, version 1.0.

An NFC bounding interval annotator sets values for the `Call Start Index`
and `Call End Index` annotations for a clip containing a nocturnal flight
call (NFC). If the annotations already exist their values are overwritten,
and if they do not already exist they are created. The clip is assumed to
contain an NFC.
"""


from collections import defaultdict
import logging

import numpy as np
import resampy
import tensorflow as tf

from vesper.command.annotator import Annotator as AnnotatorBase
from vesper.django.app.models import AnnotationInfo
from vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.inferrer \
    import Inferrer
from vesper.singletons import clip_manager
from vesper.util.settings import Settings
import vesper.django.app.model_utils as model_utils
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator_utils \
    as annotator_utils
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.dataset_utils \
    as dataset_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.yaml_utils as yaml_utils


_CLASSIFICATION_ANNOTATION_NAME = 'Classification'
_START_INDEX_ANNOTATION_NAME = 'Call Start Index'
_END_INDEX_ANNOTATION_NAME = 'Call End Index'


class Annotator(AnnotatorBase):
    
    
    extension_name = 'MPG Ranch NFC Bounding Interval Annotator 1.0'

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        logging.getLogger('tensorflow').setLevel(logging.WARN)
        
        self._clip_manager = clip_manager.instance

        self._inferrers = dict((t, Inferrer(t)) for t in ('Tseep',))
               
        self._annotation_infos = _get_annotation_infos()
        
 
    def annotate_clips(self, clips):
        
        clip_lists = self._get_call_clip_lists(clips)
        
        annotated_clip_count = 0
        
        for clip_type, clips in clip_lists.items():
            
            inferrer = self._inferrers.get(clip_type)
            
            if inferrer is not None:
                # have inferrer for this clip type
                
                inference_sample_rate = inferrer.sample_rate
                
                clips, waveform_dataset = \
                    self._get_clip_waveforms(clips, inference_sample_rate)
                
                bounds = inferrer.get_call_bounds(waveform_dataset)
                
                for clip, (start_index, end_index) in zip(clips, bounds):
                    
                    self._annotate_clip(
                        clip, _START_INDEX_ANNOTATION_NAME, start_index,
                        inference_sample_rate)
                    
                    self._annotate_clip(
                        clip, _END_INDEX_ANNOTATION_NAME, end_index,
                        inference_sample_rate)
                    
                annotated_clip_count += len(clips)
                
        return annotated_clip_count
        
        
    def _get_call_clip_lists(self, clips):
        
        """Gets a mapping from clip types to lists of call clips."""
        
        
        # Get mapping from clip types to call clip lists.
        clip_lists = defaultdict(list)
        for clip in clips:
            if _is_call_clip(clip):
                clip_type = model_utils.get_clip_type(clip)
                clip_lists[clip_type].append(clip)
        
        return clip_lists
    
    
    def _get_clip_waveforms(self, clips, inference_sample_rate):
        
        result_clips = []
        waveforms = []

        for clip in clips:
            
            try:
                waveform = self._get_clip_samples(clip, inference_sample_rate)
                
            except Exception as e:
                
                logging.warning(
                    f'Could not annotate clip "{clip}", since its samples '
                    f'could not be obtained. Error message was: {str(e)}')
                
            else:
                # got clip samples
                
                result_clips.append(clip)
                waveforms.append(waveform)
                
        waveforms = \
            dataset_utils.create_waveform_dataset_from_tensors(waveforms)
                        
        return result_clips, waveforms
                
        
    def _get_clip_samples(self, clip, inference_sample_rate):
         
        # Get clip samples.
        samples = self._clip_manager.get_samples(clip)
            
        if clip.sample_rate != inference_sample_rate:
            # need to resample
            
            samples = resampy.resample(
                samples, clip.sample_rate, inference_sample_rate)
             
        return samples


    def _annotate_clip(
            self, clip, annotation_name, index, inference_sample_rate):
        
        # If needed, modify index to account for difference between
        # clip and inference sample rates.
        if clip.sample_rate != inference_sample_rate:
            factor = clip.sample_rate / inference_sample_rate
            index = int(round(index * factor))
            
        # Make index a recording index rather than a clip index.
        index += clip.start_index
            
        annotation_info = self._annotation_infos[annotation_name]
        annotation_value = str(index)
        
        model_utils.annotate_clip(
            clip, annotation_info, annotation_value,
            creating_user=self._creating_user,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)
        
        
# class _Annotator:
#     
#     
#     def __init__(self, clip_type):
#         self.clip_type = clip_type
#         self._model = self._load_model()
#         self._settings = self._load_settings()
#         self._clip_manager = clip_manager.instance
#     
#     
#     def _load_model(self):
#         model_name = _MODEL_NAMES[self.clip_type]
#         dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
#             self.clip_type, model_name)
#         model = tf.keras.models.load_model(dir_path)
#         return model
#         
#         
#     def _load_settings(self):
#         model_name = _MODEL_NAMES[self.clip_type]
#         file_path = annotator_utils.get_model_settings_file_path(
#             self.clip_type, model_name)
#         logging.info(
#             'Loading annotator settings from "{}"...'.format(file_path))
#         text = file_path.read_text()
#         d = yaml_utils.load(text)
#         return Settings.create_from_dict(d)
#         
#         
#     def annotate_clips(self, clips):
#         
#         call_clips, waveforms = self._get_call_clip_waveforms(clips)
#         
#         if len(call_clips) == 0:
#             return []
#         
#         else:
#             # got at least one call clip waveform
#         
#             dataset = dataset_utils.create_inference_dataset(
#                 waveforms, self._settings)
#             
#             bounds = tuple(
#                 self._get_call_bounds(*slices) for slices in dataset)
#             
#             return self._convert_clip_indices_to_recording_indices(
#                 call_clips, bounds)
#     
#     
#     def _get_call_clip_waveforms(self, clips):
#         
#         call_clips = []
#         waveforms = []
# 
#         for clip in clips:
#             
#             if _is_call_clip(clip):
# 
#                 try:
#                     waveform = self._get_clip_samples(clip)
#                     
#                 except Exception as e:
#                     
#                     logging.warning(
#                         f'Could not annotate clip "{clip}", since its samples '
#                         f'could not be obtained. Error message was: {str(e)}')
#                     
#                 else:
#                     # got clip samples
#                     
#                     call_clips.append(clip)
#                     waveforms.append(waveform)
#                         
#         return call_clips, waveforms
#                 
#         
#     def _get_clip_samples(self, clip):
#          
#         # Get clip samples.
#         samples = self._clip_manager.get_samples(clip)
#             
#         annotator_sample_rate = self._settings.waveform_sample_rate
# 
#         if clip.sample_rate != annotator_sample_rate:
#             # need to resample
#             
#             samples = resampy.resample(
#                 samples, clip.sample_rate, annotator_sample_rate)
#              
#         return samples
# 
# 
#     def _get_call_bounds(self, forward_gram_slices, backward_gram_slices):
#         return (
#             self._get_call_start_index(forward_gram_slices),
#             self._get_call_end_index(backward_gram_slices))
#         
#         
#     def _get_call_start_index(self, gram_slices):
#         start_index = self._get_call_bound_index(gram_slices)
#         return self._gram_index_to_waveform_index(start_index)
#     
#     
#     def _get_call_bound_index(self, gram_slices):
#         scores = self._model.predict(gram_slices).flatten()
#         return np.argmax(scores) + self._settings.call_bound_index_offset
#     
#     
#     def _gram_index_to_waveform_index(self, gram_index):
#         
#         s = self._settings
#         
#         # Get center time of window from which spectrum was computed.
#         window_size = s.spectrogram_window_size
#         hop_size = window_size * s.spectrogram_hop_size / 100
#         time = gram_index * hop_size + window_size / 2
#         
#         # Get index of waveform sample closest to center time.
#         waveform_index = int(round(time * s.waveform_sample_rate))
#         
#         return waveform_index
#     
#         
#     def _get_call_end_index(self, gram_slices):
#         
#         end_index = self._get_call_bound_index(gram_slices)
#         
#         # Recover spectrogram length from slices shape.
#         shape = gram_slices.shape
#         slice_count = shape[0]
#         slice_length = shape[1]
#         gram_length = slice_count + slice_length - 1
#         
#         # Complement end index to account for backward order of slices
#         # and spectra within them.
#         end_index = gram_length - 1 - end_index
#         
#         return self._gram_index_to_waveform_index(end_index)
#     
#     
#     def _convert_clip_indices_to_recording_indices(self, clips, bounds):
#         return tuple(
#             self._convert_clip_indices_to_recording_indices_aux(c, *b)
#             for c, b in zip(clips, bounds))
# 
# 
#     def _convert_clip_indices_to_recording_indices_aux(
#             self, clip, start_clip_index, end_clip_index):
#         
#         sample_rate = self._settings.waveform_sample_rate
#         
#         start_recording_index = _convert_clip_index_to_recording_index(
#             clip, start_clip_index, sample_rate)
#         
#         end_recording_index = _convert_clip_index_to_recording_index(
#             clip, end_clip_index, sample_rate)
#         
#         return clip, start_recording_index, end_recording_index
        
        
def _get_annotation_infos():
    return dict(
        (name, _get_annotation_info(name))
        for name in (_START_INDEX_ANNOTATION_NAME, _END_INDEX_ANNOTATION_NAME))


def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(name=name)
    except AnnotationInfo.DoesNotExist:
        raise ValueError(f'Unrecognized annotation "{name}".')


def _is_call_clip(clip):
    annotations = model_utils.get_clip_annotations(clip)
    classification = annotations.get(_CLASSIFICATION_ANNOTATION_NAME)
    return classification is not None and classification.startswith('Call')


def _convert_clip_index_to_recording_index(
        clip, clip_index, sample_rate):
    
    if sample_rate != clip.sample_rate:
        clip_index = int(round(clip_index * clip.sample_rate / sample_rate))
        
    return clip.start_index + clip_index
