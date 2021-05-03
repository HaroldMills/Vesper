"""Module containing class `ExportCommand`."""


import logging

from vesper.command.clip_set_command import ClipSetCommand
from vesper.command.command import CommandSyntaxError
from vesper.singleton.extension_manager import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.text_utils as text_utils


_logger = logging.getLogger()


class ExportCommand(ClipSetCommand):
    
    
    extension_name = 'export'
    
    
    def __init__(self, args):
        
        super().__init__(args, False)
        
        get = command_utils.get_required_arg
        self._exporter_spec = get('exporter', args)
        
        self._exporter = self._create_exporter()
        
        
    def _create_exporter(self):
        
        try:
            name, arguments = _parse_exporter_spec(self._exporter_spec)
            return _create_exporter(name, arguments)
        
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Exporter construction')
            
        
    def execute(self, job_info):
        
        self._exporter.begin_exports()
    
        value_tuples = self._create_clip_query_values_iterator()
        
        for station, mic_output, date, detector in value_tuples:
            
            clips = _get_clips(
                station, mic_output, date, detector, self._annotation_name,
                self._annotation_value, self._tag_name)
            
            count = clips.count()
            count_text = text_utils.create_count_text(count, 'clip')
            
            _logger.info(
                f'Exporter will visit {count_text} for station '
                f'"{station.name}", mic output "{mic_output.name}", '
                f'date {date}, and detector {detector.name}.')
            
            try:
                _export_clips(clips, self._exporter)
                    
            except Exception:
                _logger.error(
                    'Clip export failed. See below for exception traceback.')
                raise
            
        self._exporter.end_exports()
            
        return True


def _parse_exporter_spec(spec):
    
    try:
        name = spec['name']
    except KeyError:
        raise CommandSyntaxError('Missing required exporter name.')
    
    arguments = spec.get('arguments', {})
    
    return name, arguments


def _create_exporter(name, arguments):
    
    classes = extension_manager.get_extensions('Exporter')
    
    try:
        cls = classes[name]
    except KeyError:
        raise ValueError(f'Unrecognized exporter "{name}".')
    
    return cls(arguments)


def _get_clips(
        station, mic_output, date, detector, annotation_name,
        annotation_value, tag_name):
    
    try:
        return model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=detector,
            annotation_name=annotation_name,
            annotation_value=annotation_value,
            tag_name=tag_name)
        
    except Exception as e:
        command_utils.log_and_reraise_fatal_exception(e, 'Clip query')
    
    
def _create_clip_count_text(count):
    suffix = '' if count == 1 else 's'
    return f'{count} clip{suffix}'
        

_LOGGING_PERIOD = 500    # clips


def _export_clips(clips, exporter):
    
    visited_count = 0
    exported_count = 0
    
    for clip in clips:
        
        if exporter.export(clip):
            exported_count += 1
        
        visited_count += 1
        
        if visited_count % _LOGGING_PERIOD == 0:
            _logger.info(f'Visited {visited_count} clips...')
            
    _logger.info(
        f'Exported {exported_count} of {visited_count} visited clips.')
