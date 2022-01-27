"""Module containing class `ExportCommand`."""


import logging
import time

# from django.db import connection

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
        
        # initial_query_count = len(connection.queries)

        start_time = time.time()
        total_visited_count = 0
        total_exported_count = 0

        exporter = self._exporter

        select_related_args = exporter.clip_query_set_select_related_args

        exporter.begin_exports()
    
        value_tuples = self._create_clip_query_values_iterator()
        
        for station, mic_output, date, detector in value_tuples:
            
            clips = _get_clips(
                station, mic_output, date, detector, self._annotation_name,
                self._annotation_value, self._tag_name)
            
            if select_related_args is not None:
                clips = clips.select_related(*select_related_args)

            clip_count = clips.count()
            count_text = text_utils.create_count_text(clip_count, 'clip')
            
            _logger.info(
                f'Exporter will visit {count_text} for station '
                f'"{station.name}", mic output "{mic_output.name}", '
                f'date {date}, and detector {detector.name}.')
            
            exporter.begin_subset_exports(
                station, mic_output, date, detector, clip_count)

            try:
                visited_count, exported_count = \
                    _export_clips(clips, exporter)
                    
            except Exception:
                _logger.error(
                    'Clip export failed. See below for exception traceback.')
                raise

            # final_query_count = len(connection.queries)
            # for i, query in enumerate(connection.queries):
            #     if i >= initial_query_count:
            #         print()
            #         print(i + 1, query)
            # print()
            # query_count = final_query_count - initial_query_count
            # print(f'Made {query_count} queries.')

            total_visited_count += visited_count
            total_exported_count += exported_count
        
            exporter.end_subset_exports()

        exporter.end_exports()

        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_exported_count, 'clips')

        _logger.info(
            f'Command exported a total of {total_exported_count} '
            f'of {total_visited_count} visited clips{timing_text}.')

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
    
    
_LOGGING_PERIOD = 500    # clips


def _export_clips(clips, exporter):
    
    start_time = time.time()
    
    visited_count = 0
    exported_count = 0
    
    for clip in clips:
        
        if exporter.export(clip):
            exported_count += 1
        
        visited_count += 1
        
        if visited_count % _LOGGING_PERIOD == 0:
            _logger.info(f'Visited {visited_count} clips...')
            
    elapsed_time = time.time() - start_time
    timing_text = command_utils.get_timing_text(
        elapsed_time, exported_count, 'clips')

    _logger.info(
        f'Exported {exported_count} of {visited_count} visited clips'
        f'{timing_text}.')

    return visited_count, exported_count
