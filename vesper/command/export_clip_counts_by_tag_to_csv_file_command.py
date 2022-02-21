"""Module containing class `ExportClipCountsByTagToCsvFileCommand`."""


from collections import namedtuple, defaultdict
import logging

from django.db import connection

from vesper.command.command import Command
import vesper.command.command_utils as command_utils


# TODO: Allow user specification of sets of detectors, sensors, dates, and
#       tag names of clips to count.


_logger = logging.getLogger()


_CLIP_COUNT_QUERY = f'''
SELECT
    vesper_processor.name AS detector_name,
    vesper_station.name AS station_name,
    vesper_clip.date AS date,
    vesper_tag_info.name AS tag_name,
    count(*)
FROM
    vesper_clip
INNER JOIN vesper_tag
    ON vesper_clip.id = vesper_tag.clip_id
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_station
    ON vesper_station.id = vesper_clip.station_id
INNER JOIN vesper_tag_info
    ON vesper_tag_info.id = vesper_tag.info_id
GROUP BY
    detector_name,
    station_name,
    date,
    tag_name
'''.lstrip()


_OUTPUT_FILE_HEADER = ('Detector', 'Station', 'Date', 'Tag', 'Clips')


_Row = namedtuple(
    '_Row',
    ('detector_name', 'station_name', 'date', 'tag_name', 'clip_count'))


class ExportClipCountsByTagToCsvFileCommand(Command):
    
    
    extension_name = 'export_clip_counts_by_tag_to_csv_file'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._output_file_path = get('output_file_path', args)
        
        
    def execute(self, job_info):

        _logger.info('Querying archive database...')
        rows = self._query_database()

        _logger.info('Writing output file...')
        command_utils.write_csv_file(
            self._output_file_path, rows, _OUTPUT_FILE_HEADER)

        return True


    def _query_database(self):

        try:
            with connection.cursor() as cursor:
                cursor.execute(_CLIP_COUNT_QUERY)
                rows = cursor.fetchall()
        except Exception as e:
            command_utils.handle_command_execution_error(
                'Database query failed.', e)

        return [_Row(*r) for r in rows]
