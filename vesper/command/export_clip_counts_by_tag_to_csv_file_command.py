"""Module containing class `ExportClipCountsByTagToCsvFileCommand`."""


from collections import namedtuple, defaultdict
from pathlib import Path
import csv
import itertools
import logging
import tempfile

from django.db import connection

from vesper.command.command import Command, CommandExecutionError
import vesper.command.command_utils as command_utils
import vesper.util.os_utils as os_utils


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


def _get_csv_file_header():
    return ('Detector', 'Station', 'Date', 'Tag', 'Clips')


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
        self._write_csv_file(rows)

        return True


    def _query_database(self):

        try:
            with connection.cursor() as cursor:
                cursor.execute(_CLIP_COUNT_QUERY)
                rows = cursor.fetchall()
        except Exception as e:
            self._handle_error('Database query failed.', e)

        return [_Row(*r) for r in rows]


    def _handle_error(self, message, e):
        raise CommandExecutionError(f'{message} Error message was: {str(e)}.')
    
    
    def _write_csv_file(self, rows):
        
        # Create output CSV file in temporary file directory.
        try:
            temp_file = tempfile.NamedTemporaryFile(
                'wt', newline='', prefix='vesper-', suffix='.csv',
                delete=False)
        except Exception as e:
            self._handle_error('Could not open output file.', e)
        
        # Create CSV writer.
        try:
            writer = csv.writer(temp_file)
        except Exception as e:
            self._handle_error('Could not create output file CSV writer.', e)

        # Write header.
        header = _get_csv_file_header()
        try:
            writer.writerow(header)
        except Exception as e:
            self._handle_error('Could not write output file header.', e)

        # Write data rows.
        try:
            writer.writerows(rows)
        except Exception as e:
            self._handle_error('Could not write output file data rows.', e)

        temp_file_path = Path(temp_file.name)
        
        # Close output file.
        try:
            temp_file.close()
        except Exception as e:
            self._handle_error('Could not close output file.', e)
        
        # Copy temporary output file to specified path.
        try:
            os_utils.copy_file(temp_file_path, self._output_file_path)
        except Exception as e:
            self._handle_error(
                'Could not copy temporary output file to specified path.', e)
