"""Module containing class `ExportCommand`."""


import logging

from django.db import transaction

from vesper.command.command import Command, CommandSyntaxError
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils


_logger = logging.getLogger()


class ExportCommand(Command):
    
    
    extension_name = 'export'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._exporter_spec = get('exporter', args)
        self._detector_names = get('detectors', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        self._exporter = self._create_exporter()
        
        
    def _create_exporter(self):
        
        try:
            name, arguments = _parse_exporter_spec(self._exporter_spec)
            return _create_exporter(name, arguments)
        except Exception as e:
            _log_fatal_exception('Exporter construction failed.', e)
            raise
            
        
    def execute(self, job_info):
        
        # Create clip iterator.
        try:
            clips = model_utils.create_clip_iterator(
                self._detector_names,
                self._sm_pair_ui_names,
                self._start_date,
                self._end_date)
        except Exception as e:
            _log_fatal_exception('Clip iterator construction failed.', e)
            raise
        
        try:
            
            # TODO: Do we need to use a transaction here? Can this cause
            # performance problems? Consider interactions among commands
            # that may run simultaneously. Keep in mind that classification
            # is idempotent: it should be harmless to run a classifier on
            # a clip more than once, say if a classification command is
            # re-run after being interrupted.
            with transaction.atomic():
                _export_clips(clips, self._exporter)
                
        except Exception:
            _logger.error(
                'Clip export failed. See below for exception traceback.')
            raise
            
        return True


def _parse_exporter_spec(spec):
    
    try:
        name = spec['name']
    except KeyError:
        raise CommandSyntaxError('Missing required exporter name.')
    
    arguments = spec.get('arguments', {})
    
    return name, arguments


def _create_exporter(name, arguments):
    
    classes = extension_manager.instance.get_extensions('Exporter')
    
    try:
        cls = classes[name]
    except KeyError:
        raise ValueError('Unrecognized exporter "{}".'.format(name))
    
    return cls(arguments)


def _log_fatal_exception(message_prefix, exception):
    _logger.error((
        '{}\n'
        'The exception message was:\n'
        '    {}\n'
        'The archive was not modified.\n'
        'See below for exception traceback.').format(
            message_prefix, str(exception)))


_LOGGING_PERIOD = 1000    # clips


def _export_clips(clips, exporter):
    
    exporter.begin_exports()
    
    count = 0
    
    for clip in clips:
        
        exporter.export(clip)
        
        count += 1
        
        if count % _LOGGING_PERIOD == 0:
            _logger.info('Exported {} clips...'.format(count))
            
    exporter.end_exports()
            
    _logger.info('Exported a total of {} clips.'.format(count))
