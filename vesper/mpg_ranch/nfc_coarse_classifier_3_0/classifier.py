"""
Module containing MPG Ranch NFC coarse classifier, version 3.0.

An NFC coarse classifier classifies an unclassified clip as a `'Call'`
if it appears to be a nocturnal flight call, or as a `'Noise'` otherwise.
It does not classify a clip that has already been classified, whether
manually or automatically.
"""


from collections import defaultdict
import logging

import numpy as np
import resampy
import tensorflow as tf
import yaml

from vesper.command.annotator import Annotator
from vesper.singletons import clip_manager
from vesper.util.settings import Settings
import vesper.django.app.model_utils as model_utils
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier_utils as \
    classifier_utils
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.dataset_utils as \
    dataset_utils
import vesper.util.signal_utils as signal_utils
from vesper.django.app.views import clip


_TESTING = True
"""`True` if classifier should run in test mode."""


class Classifier(Annotator):
    
    
    extension_name = 'MPG Ranch NFC Coarse Classifier 3.0'

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        tf.logging.set_verbosity(tf.logging.WARN)
        
        self._classifiers = dict(
            (t, _Classifier(t)) for t in ('Tseep',))
        
        
    def annotate_clips(self, clips):
        
        """Annotates the specified clips with the appropriate classifiers."""
        
        
        unclassified_clips = self._get_unclassified_clips(clips)
        
        num_clips_classified = 0
        
        for clip_type, clips in unclassified_clips.items():
            
            classifier = self._classifiers.get(clip_type)
            
            if classifier is not None:
                # have classifier for this clip type
                
                num_clips_classified += self._annotate_clips(clips, classifier)
                
        return num_clips_classified
                
                
    def _get_unclassified_clips(self, clips):
        
        """Gets a mapping from clip types to lists of unclassified clips."""
        
        
        unclassified_clips = defaultdict(list)
        
        for clip in clips:
            
            if _TESTING or self._get_annotation_value(clip) is None:
                # clip is unclassified
                
                clip_type = model_utils.get_clip_type(clip)
                unclassified_clips[clip_type].append(clip)
                
        return unclassified_clips
 

    def _annotate_clips(self, clips, classifier):
        
        """Annotates the specified clips with the specified classifier."""
        
        
        num_clips_classified = 0
            
        triples = classifier.classify_clips(clips)
        
        if _TESTING and len(triples) > 0:
            self._show_classification_errors(triples)
        
        for clip, classification, _ in triples:
            if classification is not None:
                # self._annotate(clip, classification)
                num_clips_classified += 1
                                 
        return num_clips_classified

        
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
        
        self._clip_type = clip_type
        
        self._keras_model = self._create_keras_model()
        self._estimator = self._create_estimator()
        self._settings = self._load_settings()
        
        # Configure waveform slicing.
        s = self._settings
        fs = s.waveform_sample_rate
        s2f = signal_utils.seconds_to_frames
        self._start_index = s2f(s.waveform_start_time, fs)
        length = s2f(s.waveform_duration, fs)
        self._end_index = self._start_index + length
        
        self._min_clip_duration = s.waveform_start_time + s.waveform_duration
        
        self._classification_threshold = \
            self._settings.classification_threshold

        self._clip_manager = clip_manager.instance
    
    
    def _create_keras_model(self):
        path = str(classifier_utils.get_model_file_path(self._clip_type))
        logging.info('Loading classifier model from "{}"...'.format(path))
        return tf.keras.models.load_model(path)
    
    
    def _create_estimator(self):
        path = str(classifier_utils.get_model_dir_path(self._clip_type))
        logging.info((
            'Creating TensorFlow estimator with model directory '
            '"{}"...').format(path))
        return tf.keras.estimator.model_to_estimator(
            keras_model=self._keras_model,
            model_dir=path)

    
    def _load_settings(self):
        path = classifier_utils.get_settings_file_path(self._clip_type)
        logging.info('Loading classifier settings from "{}"...'.format(path))
        text = path.read_text()
        d = yaml.load(text)
        return Settings.create_from_dict(d)
        
        
    def classify_clips(self, clips):
        
        logging.info('Collecting clip waveforms for scoring...')
        
        waveforms, indices = self._slice_clip_waveforms(clips)
        
        if len(waveforms) == 0:
            return []
        
        else:
            # have at least one waveform slice to classify
        
            # Stack waveform slices to make 2-D NumPy array.
            self._waveforms = np.stack(waveforms)
        
            logging.info('Scoring clip waveforms...')
            
            scores = classifier_utils.score_dataset_examples(
                self._estimator, self._create_dataset)
            
            logging.info('Classifying clips...')
            
            triples = [
                self._classify_clip(i, score, clips)
                for i, score in zip(indices, scores)]
            
            return triples
    
    
    def _slice_clip_waveforms(self, clips):
        
        waveforms = []
        indices = []
        
        for i, clip in enumerate(clips):
            
            waveform = self._get_clip_samples(clip)
            
            if len(waveform) < self._end_index:
                # clip too short to classify
                
                logging.warning((
                    'Classification failed for clip "{}", since it is '
                    'shorter than the required {:.3f} seconds.').format(
                        str(clip), self._min_clip_duration))
                
            else:
                # clip not too short to classify
                
                # Slice waveform for classifier.
                waveform = waveform[self._start_index:self._end_index]
                
                waveforms.append(waveform)
                indices.append(i)
                
        return waveforms, indices
                
        
    def _get_clip_samples(self, clip):
         
        samples = self._clip_manager.get_samples(clip)
        sample_rate = clip.sample_rate
         
        classifier_sample_rate = self._settings.waveform_sample_rate
         
        if sample_rate != classifier_sample_rate:
            # samples are not at classifier sample rate
            
            samples = resampy.resample(
                samples, sample_rate, classifier_sample_rate)
             
        return samples

        
    def _create_dataset(self):
        
        model_input_name = self._keras_model.input_names[0]
        
        return dataset_utils.create_spectrogram_dataset_from_waveforms_array(
            self._waveforms, dataset_utils.DATASET_MODE_INFERENCE,
            self._settings, batch_size=64, feature_name=model_input_name)
    
    
    def _classify_clip(self, index, score, clips):
        
        if score >= self._classification_threshold:
            classification = 'Call'
        else:
            classification = 'Noise'

        return clips[index], classification, score
