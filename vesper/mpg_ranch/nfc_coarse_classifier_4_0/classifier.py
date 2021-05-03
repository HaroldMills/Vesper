"""
Module containing MPG Ranch NFC coarse classifier, version 4.0.

An NFC coarse classifier classifies an unclassified clip as a `'Call'`
if it appears to be a nocturnal flight call, or as a `'Noise'` otherwise.
It does not classify a clip that has already been classified, whether
manually or automatically.

This classifier was trained on clips created by the Old Bird Tseep
and Thrush Redux 1.1 detectors from MPG Ranch recordings collected in
the fall of 2017 and the fall of 2018.
"""


from collections import defaultdict
import logging

import numpy as np
import resampy
import tensorflow as tf

from vesper.command.annotator import Annotator
from vesper.django.app.models import AnnotationInfo
from vesper.singleton.clip_manager import clip_manager
from vesper.util.settings import Settings
import vesper.django.app.model_utils as model_utils
import vesper.mpg_ranch.nfc_coarse_classifier_4_0.classifier_utils as \
    classifier_utils
import vesper.mpg_ranch.nfc_coarse_classifier_4_0.dataset_utils as \
    dataset_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.yaml_utils as yaml_utils


_EVALUATION_MODE_ENABLED = False

_FN_THRESHOLD = .20
"""
Evaluation mode false negative score threshold.

The value of this attribute should be either a score value in [0, 1] or
`None`. If a score value, "Call*" clips whose scores do not exceed the
threshold will be reclassified as "FN*". If `None`, no clips will be
reclassified as "FN*".
"""

_FP_THRESHOLD = None
"""
Evaluation mode false positive score threshold.

The value of this attribute should be either a score value in [0, 1] or
`None`. If a score value, "Noise" clips whose scores are at least the
threshold will be reclassified as "FP". If `None`, no clips will be
reclassified as "FP".
"""


'''
This classifier can run in one of two modes, *normal mode* and
*evaluation mode*. In normal mode, it annotates only unclassified clips,
assigning to each a "Classification" annotation value or either "Call"
or "Noise".

In evaluation mode, the classifier classifies every clip whose clip type
(e.g. "Tseep" or "Thrush") it recognizes and that already has a
classification that is "Noise" or starts with "Call" or "XCall".
The new classification is a function of both the existing classification
and the *normal classification* that the classifier would assign to the
clip in normal mode if it had no existing classification. The new
classifications are as follows (where the classification pairs are
(existing classification, normal classification)):

    (Noise, Noise) -> Noise (i.e. no change)
    (Noise, Call) -> FP
    (Call*, Call) -> Call* (i.e. no change)
    (Call*, Noise) -> FN* (i.e. only coarse part changes)
    (XCall*, Call) -> XCallP* (i.e. only coarse part changes)
    (XCall*, Noise) -> XCallN* (i.e. only coarse part changes)
    
This reclassifies clips for which the normal classification differs from
the existing classification in such a way that important sets of clips
(i.e. false positives, false negatives, excluded call positives, and
excluded call negatives) can subsequently be viewed in clip albums.
'''


class Classifier(Annotator):
    
    
    extension_name = 'MPG Ranch NFC Coarse Classifier 4.0'

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        tf.logging.set_verbosity(tf.logging.WARN)
        
        self._classifiers = dict(
            (t, _Classifier(t)) for t in ('Tseep', 'Thrush'))
        
        if _EVALUATION_MODE_ENABLED:
            self._score_annotation_info = \
                AnnotationInfo.objects.get(name='Detector Score')
        
        
    def annotate_clips(self, clips):
        
        """Annotates the specified clips with the appropriate classifiers."""
        
        
        clip_lists = self._get_clip_lists(clips)
        
        num_clips_classified = 0
        
        for clip_type, clips in clip_lists.items():
            
            classifier = self._classifiers.get(clip_type)
            
            if classifier is not None:
                # have classifier for this clip type
                
                num_clips_classified += self._annotate_clips(clips, classifier)
                
        return num_clips_classified
                
                
    def _get_clip_lists(self, clips):
        
        """Gets a mapping from clip types to lists of clips to classify."""
        
        
        clip_lists = defaultdict(list)
        
        for clip in clips:
            
            if _EVALUATION_MODE_ENABLED or \
                    self._get_annotation_value(clip) is None:
                # clip should be classified
                
                clip_type = model_utils.get_clip_type(clip)
                clip_lists[clip_type].append(clip)
                
        return clip_lists
 

    def _annotate_clips(self, clips, classifier):
        
        """Annotates the specified clips with the specified classifier."""
        
        
        num_clips_classified = 0
            
        triples = classifier.classify_clips(clips)
        
        # if _EVALUATION_MODE_ENABLED and len(triples) > 0:
        #     self._show_classification_errors(triples)
        
        for clip, auto_classification, score in triples:
            
            if auto_classification is not None:
                
                if _EVALUATION_MODE_ENABLED:
                    
                    old_classification = self._get_annotation_value(clip)
                
                    new_classification = self._get_new_classification(
                        old_classification, auto_classification, score)
                    
                    if new_classification is not None:
                        self._annotate(clip, new_classification)
                        num_clips_classified += 1
                        
                    self._set_clip_score(clip, score)
                        
                else:
                    # normal mode
                    
                    self._annotate(clip, auto_classification)
                    num_clips_classified += 1
                        
        return num_clips_classified

        
    def _get_new_classification(
            self, old_classification, auto_classification, score):
        
        old = old_classification
        auto = auto_classification
        
        if old is None:
            return None
        
        elif old.startswith('Call') and auto == 'Noise':
            # false negative
            
            if _FN_THRESHOLD is not None and score <= _FN_THRESHOLD:
                return 'FN' + old[len('Call'):]
            
            else:
                return None
            
        elif old == 'Noise' and auto == 'Call':
            # false positive
            
            if _FP_THRESHOLD is not None and score >= _FP_THRESHOLD:
                return 'FP'
            
            else:
                return None
           
        else:
            return None


    def _set_clip_score(self, clip, score):
        
        value = '{:.3f}'.format(100 * score)
                    
        model_utils.annotate_clip(
            clip, self._score_annotation_info, value,
            creating_user=self._creating_user,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)
                    

    def _show_classification_errors(self, triples):
          
        num_positives = 0
        num_negatives = 0
        false_positives = []
        false_negatives = []
          
        for i, (clip, new_classification, score) in enumerate(triples):
              
            old_classification = self._get_annotation_value(clip)
              
            if old_classification.startswith('Call'):
                  
                num_positives += 1
                  
                if new_classification == 'Noise':
                    false_negatives.append(
                        (i, old_classification, new_classification, score))
                      
            else:
                # old classification does not start with 'Call'
                  
                num_negatives += 1
                  
                if new_classification == 'Call':
                    false_positives.append(
                        (i, old_classification, new_classification, score))
                      
        num_clips = len(triples)
        logging.info('Classified {} clips.'.format(num_clips))
           
        self._show_classification_errors_aux(
            'calls', false_negatives, num_positives)
           
        self._show_classification_errors_aux(
            'non-calls', false_positives, num_negatives)
           
        num_errors = len(false_positives) + len(false_negatives)
        accuracy = 100 * (1 - num_errors / num_clips)
        logging.info(
            'The overall accuracy was {:.1f} percent.'.format(accuracy))
            

    def _show_classification_errors_aux(self, category, errors, num_clips):
        
        num_errors = len(errors)
        percent = 100 * num_errors / num_clips
        
        logging.info((
            '{} of {} {} ({:.1f} percent) where incorrectly '
            'classified:').format(num_errors, num_clips, category, percent))
        
        for i, old_classification, new_classification, score in errors:
            
            logging.info(
                '    {} {} -> {} {}'.format(
                    i, old_classification, new_classification, score))


class _Classifier:
    
    
    def __init__(self, clip_type):
        
        self.clip_type = clip_type
        
        self._estimator = self._create_estimator()
        self._settings = self._load_settings()
        
        # Configure waveform slicing.
        s = self._settings
        fs = s.waveform_sample_rate
        s2f = signal_utils.seconds_to_frames
        self._waveform_start_time = \
            s.waveform_start_time + s.inference_waveform_start_time_offset
        self._waveform_duration = s.waveform_duration
        self._waveform_length = s2f(self._waveform_duration, fs)
        
        self._classification_threshold = \
            self._settings.classification_threshold
    
    
    def _create_estimator(self):
        path = classifier_utils.get_tensorflow_model_dir_path(self.clip_type)
        logging.info((
            'Creating TensorFlow estimator from saved model in directory '
            '"{}"...').format(path))
        return tf.contrib.estimator.SavedModelEstimator(str(path))

    
    def _load_settings(self):
        path = classifier_utils.get_settings_file_path(self.clip_type)
        logging.info('Loading classifier settings from "{}"...'.format(path))
        text = path.read_text()
        d = yaml_utils.load(text)
        return Settings.create_from_dict(d)
        
        
    def classify_clips(self, clips):
        
        # logging.info('Collecting clip waveforms for scoring...')
        
        waveforms, indices = self._slice_clip_waveforms(clips)
        
        if len(waveforms) == 0:
            return []
        
        else:
            # have at least one waveform slice to classify
        
            # Stack waveform slices to make 2-D NumPy array.
            self._waveforms = np.stack(waveforms)
        
            # logging.info('Scoring clip waveforms...')
            
            scores = classifier_utils.score_dataset_examples(
                self._estimator, self._create_dataset)
            
            # logging.info('Classifying clips...')
            
            triples = [
                self._classify_clip(i, score, clips)
                for i, score in zip(indices, scores)]
            
            return triples
    
    
    def _slice_clip_waveforms(self, clips):
        
        waveforms = []
        indices = []
        
        for i, clip in enumerate(clips):
            
            try:
                waveform = self._get_clip_samples(clip)
                
            except Exception as e:
                
                logging.warning((
                    'Could not classify clip "{}", since its '
                    'samples could not be obtained. Error message was: '
                    '{}').format(str(clip), str(e)))
                
            else:
                # got clip samples
                
                waveforms.append(waveform)
                indices.append(i)
                    
        return waveforms, indices
                
        
    def _get_clip_samples(self, clip):
         
        clip_sample_rate = clip.sample_rate
        classifier_sample_rate = self._settings.waveform_sample_rate

        s2f = signal_utils.seconds_to_frames
        start_offset = s2f(self._waveform_start_time, clip_sample_rate)
        
        if clip_sample_rate != classifier_sample_rate:
            # need to resample
            
            # Get clip samples, including a millisecond of padding at
            # the end. I don't know what if any guarantees the
            # `resampy.resample` function offers about the relationship
            # between its input and output lengths, so we add the padding
            # to try to ensure that we don't wind up with too few samples
            # after resampling.
            length = s2f(self._waveform_duration + .001, clip_sample_rate)
            samples = clip_manager.get_samples(
                clip, start_offset=start_offset, length=length)
            
            # Resample clip samples to classifier sample rate.
            samples = resampy.resample(
                samples, clip_sample_rate, classifier_sample_rate)
            
            # Discard any extra trailing samples we wound up with.
            samples = samples[:self._waveform_length]
            
            if len(samples) < self._waveform_length:
                raise ValueError('Resampling produced too few samples.')
            
        else:
            # don't need to resample
            
            samples = clip_manager.get_samples(
                clip, start_offset=start_offset, length=self._waveform_length)
             
        return samples

        
    def _create_dataset(self):
        
        return dataset_utils.create_spectrogram_dataset_from_waveforms_array(
            self._waveforms, dataset_utils.DATASET_MODE_INFERENCE,
            self._settings, batch_size=64,
            feature_name=self._settings.model_input_name)
    
    
    def _classify_clip(self, index, score, clips):
        
        # print(score, self._classification_threshold)
        
        if score >= self._classification_threshold:
            classification = 'Call'
        else:
            classification = 'Noise'

        return clips[index], classification, score
