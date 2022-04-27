"""
Module containing PSW NOGO coarse classifier, version 0.0.

This classifier classifies an unclassified clip as a `"NOGO"` if it
appears to contain the start of a Northern Goshawk call in its first
200 milliseconds, or as an `"Other"` otherwise. It does not classify
a clip that has already been classified, whether manually or
automatically.
"""


import logging

from vesper.command.annotator import Annotator
from vesper.django.app.models import AnnotationInfo, TagInfo
from vesper.singleton.clip_manager import clip_manager
import vesper.django.app.model_utils as model_utils
import vesper.psw.nogo_coarse_classifier_0_0.classifier_utils as \
    classifier_utils
import vesper.psw.nogo_coarse_classifier_0_0.dataset_utils as dataset_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.time_utils as time_utils


_COMPARISON_MODE_ENABLED = False


'''
This classifier can run in one of two modes, *normal mode* and
*comparison mode*. In normal mode, the classifier annotates only
unclassified clips, assigning to each a "Classification" annotation
value of either "NOGO" or "Other".

In comparison mode, the classifier does not modify any existing
classifications, but for each clip that has a classification that starts
with "NOGO" or is "Other", the classifier tags the clip as a
"False Negative" if it is a "NOGO" that the classifier would classify as
"Other", and tags the clip as a "False Positive" if it is an "Other" that
the classifier would classify as a "NOGO".
'''


class _Classifier(Annotator):
    
    
    def __init__(self, threshold, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        logging.getLogger('tensorflow').setLevel(logging.WARN)
        
        # TODO: Perhaps `Annotator.__init__` should do this.
        self._logger = logging.getLogger()

        self._model = classifier_utils.load_inference_model()
        
        self._settings = classifier_utils.load_inference_settings()
            
        self._threshold = threshold / 100
        
        if _COMPARISON_MODE_ENABLED:
            
            self._false_positive_tag_info = \
                TagInfo.objects.get(name='False Positive')
                  
            self._false_negative_tag_info = \
                TagInfo.objects.get(name='False Negative')
                
        # TODO: Perhaps `Annotator` should handle annotation info
        # creation and caching.
        self._annotation_info_cache = {}

        
    def annotate_clips(self, clips):
        
        classified_clip_count = 0
        
        annotation_values = self._get_annotation_values(clips)
        
        clips, annotation_values = self._filter_clips(clips, annotation_values)
        
        if len(clips) == 0:
            # no clips to classify
            
            return 0
        
        else:
            # at least one clip to classify
            
            dataset = self._create_dataset(clips)
            
            scores = self._model.predict(dataset).flatten()
            
            for clip, annotation_value, score in \
                    zip(clips, annotation_values, scores):
                
                self._annotate_clip_score(clip, score)
                
                if _COMPARISON_MODE_ENABLED:
                    self._tag_clip_if_needed(clip, annotation_value, score)
                
                else:
                    self._annotate_clip(clip, score)
                    classified_clip_count += 1
                    
            return classified_clip_count

                
    def _get_annotation_values(self, clips):
        return [self._get_annotation_value(c) for c in clips]
    
    
    def _filter_clips(self, clips, annotation_values):
        
        pairs = [
            (clip, value) for clip, value in zip(clips, annotation_values)
            if self._is_clip_to_classify(value)]
        
        if len(pairs) == 0:
            return (), ()
        
        else:
            # at least one clip in result
            
            return tuple(zip(*pairs))
    
    
    def _is_clip_to_classify(self, annotation_value):
        if _COMPARISON_MODE_ENABLED:
            return _is_nogo(annotation_value) or _is_other(annotation_value)
        else:
            return annotation_value is None
        

    def _create_dataset(self, clips):
        
        # TODO: Resample clip waveforms if needed. See other recent
        # classifiers for examples of this.
        waveforms = self._get_clip_waveforms(clips)
        
        # TODO: This is a workaround that compensates for a problem
        # in `dataset_utils._ExampleProcessor._slice_waveform`, which
        # works for tfrecord datasets but not for NumPy array ones.
        # Fix whatever the problem is and delete this. ZZZ
        waveforms = [w[:19200] for w in waveforms]
        
        dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
        
        dataset = \
            dataset_utils.create_inference_dataset(dataset, self._settings)
        
        return dataset
    
    
    def _get_clip_waveforms(self, clips):

        waveforms = []

        for clip in clips:

            try:
                waveform = clip_manager.get_samples(clip)

            except Exception as e:
                self._logger.warning(
                    f'Could not get samples for clip {str(clip)}, so it '
                    f'will not be classified. Error message was: {str(e)}')
                continue

            waveforms.append(waveform)

        return waveforms
        

    def _annotate_clip_score(self, clip, score):
        
        annotation_info = self._get_annotation_info('Classifier Score')
        annotation_value = str(100 * score)
        
        model_utils.annotate_clip(
            clip, annotation_info, annotation_value,
            creating_user=self._creating_user,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)
    
    
    def _get_annotation_info(self, annotation_name):
        
        try:
            return self._annotation_info_cache[annotation_name]
        
        except KeyError:
            # cache miss
            
            try:
                info = AnnotationInfo.objects.get(name=annotation_name)
            
            except AnnotationInfo.DoesNotExist:
                
                classifier_name = self.extension_name
 
                self._logger.info(
                    f'    Adding annotation "{annotation_name}" to '
                    f'archive for classifier "{classifier_name}"...')
                
                description = (
                    f'Created automatically for classifier '
                    f'"{classifier_name}".')
                
                type_ = 'String'
                creation_time = time_utils.get_utc_now()
                
                info = AnnotationInfo.objects.create(
                    name=annotation_name,
                    description=description,
                    type=type_,
                    creation_time=creation_time,
                    creating_user=self._creating_user,
                    creating_job=self._creating_job)
            
            self._annotation_info_cache[annotation_name] = info
            
            return info
    
    
    def _tag_clip_if_needed(self, clip, annotation_value, score):
        
        if _is_other(annotation_value):
            # clip is classified as "Other"
                
            if score >= self._threshold:
                # classifier would classify clip as "NOGO"
                
                self._tag(clip, self._false_positive_tag_info)
                   
        elif _is_nogo(annotation_value):
            # clip is classified as "NOGO*"
            
            if score < self._threshold:
                # classifier would classify clip as "Other"
                
                self._tag(clip, self._false_negative_tag_info)
                

    def _annotate_clip(self, clip, score):
        
        if score >= self._threshold:
            annotation_value = 'NOGO'
        else:
            annotation_value = 'Other'
            
        # TODO: `Annotator._annotate` should take an annotation name
        # as well as an annotation value.
        self._annotate(clip, annotation_value)
        
        
def _is_nogo(annotation_value):
    return annotation_value is not None and annotation_value.startswith('NOGO')


def _is_other(annotation_value):
    return annotation_value == 'Other'
    
    
class Classifier10(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 10'
    
    def __init__(self, *args, **kwargs):
        super().__init__(10, *args, **kwargs)


class Classifier20(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 20'
    
    def __init__(self, *args, **kwargs):
        super().__init__(20, *args, **kwargs)


class Classifier30(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 30'
    
    def __init__(self, *args, **kwargs):
        super().__init__(30, *args, **kwargs)


class Classifier40(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 40'
    
    def __init__(self, *args, **kwargs):
        super().__init__(40, *args, **kwargs)


class Classifier50(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 50'
    
    def __init__(self, *args, **kwargs):
        super().__init__(50, *args, **kwargs)


class Classifier60(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 60'
    
    def __init__(self, *args, **kwargs):
        super().__init__(60, *args, **kwargs)


class Classifier70(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 70'
    
    def __init__(self, *args, **kwargs):
        super().__init__(70, *args, **kwargs)


class Classifier80(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 80'
    
    def __init__(self, *args, **kwargs):
        super().__init__(80, *args, **kwargs)


class Classifier90(_Classifier):
    
    extension_name = 'PSW NOGO Coarse Classifier 0.0 90'
    
    def __init__(self, *args, **kwargs):
        super().__init__(90, *args, **kwargs)


