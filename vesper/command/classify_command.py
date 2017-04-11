"""Module containing class `ClassifyCommand`."""


import logging

from django.db import transaction

from vesper.command.command import Command
from vesper.django.app.models import AnnotationInfo
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils


_logger = logging.getLogger()


class ClassifyCommand(Command):
    
    
    extension_name = 'classify'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._classifier_name = get('classifier', args)
        self._detector_names = get('detectors', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._annotation_name = get('annotation_name', args)
        
        
    def execute(self, job_info):
        
        # Get annotation info.
        try:
            annotation_info = \
                AnnotationInfo.objects.get(name=self._annotation_name)
        except Exception as e:
            _log_fatal_exception('Get of annotation information', e)
            
        # Create classifier.
        try:
            classifier = \
                _create_classifier(self._classifier_name, annotation_info)
        except Exception as e:
            _log_fatal_exception('Classifier construction', e)
            raise
        
        # Create clip iterator.
        try:
            clips = model_utils.clip_generator(
                self._detector_names,
                self._sm_pair_ui_names,
                self._start_date,
                self._end_date)
        except Exception as e:
            _log_fatal_exception('Clip iterator construction', e)
            raise
        
        try:
            with transaction.atomic():
                _classify_clips(clips, classifier)
                
        except Exception:
            _logger.error(
                'Clip classification failed with an exception. The '
                'archive has been restored to its state before '
                'classification started. See below for exception '
                'traceback.')
            raise
            
        return True


def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(name)
    except AnnotationInfo.DoesNotExist:
        raise ValueError(
            'Unrecognized annotation "{}".'.format(name))
    
        
# TODO: Who is the authority regarding classifiers: `Processor` instances
# or the extension manager? Right now classifier names are stored redundantly
# in both `Processor` instances and the extensions, and hence there is
# the potential for inconsistency. We populate UI controls from the
# `Processor` instances, but construct classifiers using the extension
# manager, which finds extensions using the names stored in the extensions
# themselves. How might we eliminate the redundancy? Be sure to consider
# versioning and the possibility of processing parameters when thinking
# about this.
def _create_classifier(name, annotation_info):
    
    classes = extension_manager.instance.get_extensions('Classifier')
    
    try:
        cls = classes[name]
    except KeyError:
        raise ValueError('Unrecognized classifier "{}".'.format(name))
    
    return cls(annotation_info)
    
    
def _log_fatal_exception(message_prefix, exception):
    _logger.error((
        '{} failed with an exception.\n'
        'The exception message was:\n'
        '    {}\n'
        'The archive was not modified.\n'
        'See below for exception traceback.').format(
            message_prefix, str(exception)))


_LOGGING_PERIOD = 1000    # clips


def _classify_clips(clips, classifier):
    
    count = 0
    
    for clip in clips:
        
        classifier.classify(clip)
        
        count += 1
        
        if count % _LOGGING_PERIOD == 0:
            _logger.info('Classified {} clips...'.format(count))
            
    _logger.info('Classified a total of {} clips.'.format(count))
