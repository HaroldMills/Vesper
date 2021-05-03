"""Module containing class `ClassifyCommand`."""


import logging
import time

from vesper.command.command import Command
from vesper.django.app.models import AnnotationInfo, Job, Processor
from vesper.singleton.extension_manager import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.text_utils as text_utils


_logger = logging.getLogger()


class ClassifyCommand(Command):
    
    
    extension_name = 'classify'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._classifier_name = get('classifier', args)
        self._annotation_name = get('annotation_name', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._detector_names = get('detectors', args)
        self._tag_name = get('tag', args)
        

    def execute(self, job_info):
        
        classifier = self._create_classifier(job_info.job_id)
        
        classifier.begin_annotations()
    
        value_tuples = self._create_clip_query_values_iterator()
        
        tag_name = model_utils.get_clip_query_tag_name(self._tag_name)
 
        for station, mic_output, date, detector in value_tuples:
            
            clips = _get_clips(station, mic_output, date, detector, tag_name)
            
            count = clips.count()
            count_text = text_utils.create_count_text(count, 'clip')
            
            _logger.info(
                f'Classifier will visit {count_text} for station '
                f'"{station.name}", mic output "{mic_output.name}", '
                f'date {date}, and detector "{detector.name}".')
            
            try:
                _classify_clips(clips, classifier)
                    
            except Exception:
                _logger.error(
                    'Clip classification failed. See below for exception '
                    'traceback.')
                raise
            
        classifier.end_annotations()
    
        return True


    def _create_classifier(self, job_id):
        
        try:
            annotation_info = _get_annotation_info(self._annotation_name)
            job = _get_job(job_id)
            processor = _get_processor(self._classifier_name)
            return _create_classifier(
                self._classifier_name, annotation_info, job, processor)
        
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Classifier construction', 'The archive was not modified.')
        

    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._sm_pair_ui_names, self._start_date, self._end_date,
                self._detector_names)
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction')
            
            
def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(name=name)
    except AnnotationInfo.DoesNotExist:
        raise ValueError(f'Unrecognized annotation "{name}".')
    
        
def _get_job(job_id):
    try:
        return Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        raise ValueError(f'Unrecognized job ID {job_id}.')
        

def _get_processor(name):
    try:
        return Processor.objects.get(name=name, type='Classifier')
    except Processor.DoesNotExist:
        raise ValueError(f'Unrecognized processor "{name}".')
        

# TODO: Who is the authority regarding classifiers: `Processor` instances
# or the extension manager? Right now classifier names are stored redundantly
# in both `Processor` instances and the extensions, and hence there is
# the potential for inconsistency. We populate UI controls from the
# `Processor` instances, but construct classifiers using the extension
# manager, which finds extensions using the names stored in the extensions
# themselves. How might we eliminate the redundancy? Be sure to consider
# versioning and the possibility of processing parameters when thinking
# about this.
def _create_classifier(name, annotation_info, job, processor):
    
    classes = extension_manager.get_extensions('Classifier')
    
    try:
        cls = classes[name]
    except KeyError:
        raise ValueError(f'Unrecognized classifier "{name}".')
    
    return cls(annotation_info, creating_job=job, creating_processor=processor)
    
    
def _get_clips(station, mic_output, date, detector, tag_name):
    
    try:
        
        return model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=detector,
            tag_name=tag_name)
        
    except Exception as e:
        command_utils.log_and_reraise_fatal_exception(e, 'Clip query')
    
    
_LOGGING_PERIOD = 500    # clips


def _classify_clips(clips, classifier):
    
    start_time = time.time()
    
    if hasattr(classifier, 'annotate_clips'):
        classify = _classify_clip_batches
    else:
        classify = _classify_clips_individually
        
    num_clips_classified = classify(clips, classifier)

    elapsed_time = time.time() - start_time
    num_clips = len(clips)
    timing_text = command_utils.get_timing_text(
        elapsed_time, num_clips, 'clips')
            
    _logger.info(
        f'Classified {num_clips_classified} of {num_clips} visited clips'
        f'{timing_text}.')


def _classify_clip_batches(clips, classifier):
    return classifier.annotate_clips(clips)


def _classify_clips_individually(clips, classifier):
    
    num_visited_clips = 0
    num_classified_clips = 0
    
    for clip in clips:
        
        try:
            if classifier.annotate(clip):
                num_classified_clips += 1
                        
        except Exception as e:
            _logger.error(
                f'Classification failed for clip "{str(clip)}". '
                f'Error message was: {str(e)}')
        
        num_visited_clips += 1
        
        if num_visited_clips % _LOGGING_PERIOD == 0:
            _logger.info(f'Visited {num_visited_clips} clips...')
            
    return num_classified_clips
