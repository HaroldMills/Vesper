"""Module containing class `ClassifyCommand`."""


import datetime
import logging

from vesper.command.command import Command
from vesper.django.app.models import Processor
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils


_logger = logging.getLogger()

_ONE_DAY = datetime.timedelta(days=1)


class ClassifyCommand(Command):
    
    
    extension_name = 'classify'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._classifier_name = get('classifier', args)
        self._detector_names = get('detectors', args)
        self._station_mic_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, job_info):
        
        classifier = self._create_classifier()
        detectors = self._get_detectors()
        
        # TODO: Create clip iterator from command arguments.
        # Iterator must go from (station, mic_output, start_date, end_date)
        # tuples to (recording/channel num) pairs to clips.
        # self._clip_iterator = _create_clip_iterator(args)
        
        date = self._start_date
        while date <= self._end_date:
            for detector in detectors:
                for sm_name in self._station_mic_names:
                    print('ClassifyCommand', date, detector.name, sm_name)
            date += _ONE_DAY
                
        # TODO: Iterate over clips, invoking classifier for each one.
        print('ClassifyCommand.execute')
        return True

        
    def _create_classifier(self):
        processor = self._get_classifier()
        cls = _get_classifier_class(processor.name)
        return cls()


    def _get_classifier(self):
        
        try:
            return _get_processor(self._classifier_name, 'Classifier')

        except Exception as e:
            _log_fatal_exception('Getting classifier to run on clips', e)
            raise
            

    def _get_detectors(self):
        
        try:
            return [
                _get_processor(name, 'Detector')
                for name in self._detector_names]
        
        except Exception as e:
            _log_fatal_exception('Getting detectors', e)
            raise
            
            
def _get_processor(name, type):
    try:
        return model_utils.get_processor(name, type)
    except Processor.DoesNotExist:
        raise ValueError('Unrecognized {} "{}".'.format(type.lower(), name))


def _log_fatal_exception(message_prefix, exception):
    _logger.error((
        '{} failed with an exception.\n'
        'The exception message was:\n'
        '    {}\n'
        'The archive was not modified.\n'
        'See below for exception traceback.').format(
            message_prefix, str(exception)))
    
    
def _get_classifier_class(name):
    classes = extension_manager.instance.get_extensions('Classifier')
    try:
        return classes[name]
    except KeyError:
        raise ValueError('Unrecognized classifier extension "{}".'.format(name))


def _get_detectors(detector_names):
    
    try:
        return [_get_detector(name) for name in detector_names]
    
    except Exception as e:
        _logger.error((
            'Getting detectors to run on recordings on failed with '
                'an exception.\n'
            'The exception message was:\n'
            '    {}\n'
            'The archive was not modified.\n'
            'See below for exception traceback.').format(str(e)))
        raise
        
        
def _get_detector(self, name):
    try:
        return model_utils.get_processor(name, 'Detector')
    except Processor.DoesNotExist:
        raise ValueError(
            'Unrecognized detector "{}".'.format(name))
