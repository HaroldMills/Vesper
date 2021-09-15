"""
Module containing PSW NOGO coarse classifier, version 0.0.

This classifier classifies an unclassified clip as `'NOGO'` if it
appears to contain the start of a Northern Goshawk call in its first
200 milliseconds, or as  `'Other'` otherwise. It does not classify
a clip that has already been classified, whether manually or
automatically.
"""


import logging

from vesper.command.annotator import Annotator
from vesper.django.app.models import TagInfo
from vesper.singleton.clip_manager import clip_manager
import vesper.psw.nogo_coarse_classifier_0_0.classifier_utils as \
    classifier_utils
import vesper.psw.nogo_coarse_classifier_0_0.dataset_utils as dataset_utils
import vesper.util.open_mp_utils as open_mp_utils


# TODO: Rather than tagging clips with "True" or "False" for
# evaluation, it might be better to just record the classifier's
# classifications in a new annotation (named "Test Classification",
# say, or whatever the user wants) and then let the user display clips
# according to a filter that refers to both the "Classification" and
# the "Test Classification" annotations.


_EVALUATION_MODE_ENABLED = False


'''
This classifier can run in one of two modes, *normal mode* and
*evaluation mode*. In normal mode, it annotates only unclassified clips,
assigning to each a "Classification" annotation value or either "NOGO"
or "Other".

In evaluation mode, the classifier does not modify any existing
classification, but tags each clip that has a classification that is
"Other" or starts with "NOGO" with either "True" or "False", according
to whether the classifier's classification would be correct or incorrect,
respectively, assuming that the existing classifications are correct.
'''


class _Classifier(Annotator):
    
    
    def __init__(self, threshold, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        logging.getLogger('tensorflow').setLevel(logging.WARN)
        
        self._model = classifier_utils.load_inference_model()
        
        self._settings = classifier_utils.load_inference_settings()
            
        self._threshold = threshold / 100
        
        if _EVALUATION_MODE_ENABLED:
            self._true_tag_info = TagInfo.objects.get(name='True')
            self._false_tag_info = TagInfo.objects.get(name='False')
                  
        
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
                
                if _EVALUATION_MODE_ENABLED:
                    self._tag_clip(clip, annotation_value, score)
                    
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
        if _EVALUATION_MODE_ENABLED:
            return _is_nogo_or_other(annotation_value)
        else:
            return annotation_value is None
            

    def _create_dataset(self, clips):
        
        # TODO: Resample clip waveforms if needed. See other recent
        # classifiers for examples of this.
        waveforms = [clip_manager.get_samples(c) for c in clips]
        
        # TODO: This is a workaround that compensates for a problem
        # in `dataset_utils._ExampleProcessor._slice_waveform`, which
        # works for tfrecord datasets but not for NumPy array ones.
        # Fix whatever the problem is and delete this. ZZZ
        waveforms = [w[:19200] for w in waveforms]
        
        dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
        
        dataset = dataset_utils.create_inference_dataset(dataset, self._settings)
        
        return dataset
    
    
    def _tag_clip(self, clip, annotation_value, score):
        
        if _is_nogo_or_other(annotation_value):
            
            scored_nogo = score >= self._threshold
            
            scored_true = \
                scored_nogo and _is_nogo(annotation_value) or \
                not scored_nogo and _is_other(annotation_value)
                        
            if scored_true:
                self._tag(clip, self._true_tag_info)
            else:
                self._tag(clip, self._false_tag_info)
               
        
    def _annotate_clip(self, clip, score):
        
        if score >= self._threshold:
            annotation_value = 'NOGO'
        else:
            annotation_value = 'Other'
            
        self._annotate(clip, annotation_value)
        
        
def _is_nogo_or_other(annotation_value):
    return _is_nogo(annotation_value) or _is_other(annotation_value)
           
           
def _is_nogo(annotation_value):
    return annotation_value.startswith('NOGO')


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


