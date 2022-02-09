"""Module containing class `ExportClipCountsToCsvFileCommand`."""


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


# TODO: Allow specification of sets of detectors, sensors, dates, and
#       classifications of clips to count.
# TODO: Allow specification of classification annotation name.
# TODO: Support tagged clip counts.
# TODO: Optionally output estimated bird counts as well as clip counts.
#       This will require looking at clip times.


_logger = logging.getLogger()


_CLIP_COUNT_QUERY = '''
SELECT
    vesper_processor.name Detector,
    vesper_station.name Station,
    date Date,
    value Classification,
    count(*)
FROM
    vesper_clip
LEFT JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
        AND info_id = (
            SELECT id from vesper_annotation_info
            WHERE name = 'Classification')
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_station
    ON vesper_station.id = station_id
GROUP BY
    Detector,
    Station,
    Date,
    Classification
'''.lstrip()

_CLASSIFICATION_SUBSTITUTIONS = {
    None: 'Unclassified'
}

_CSV_FILE_HEADER = ('Detector', 'Station', 'Date', 'Classification', 'Clips')


_Row = namedtuple(
    'Row', ('detector', 'station', 'date', 'classification', 'clip_count'))


class ExportClipCountsToCsvFileCommand(Command):
    
    
    extension_name = 'export_clip_counts_to_csv_file'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._output_file_path = get('output_file_path', args)
        
        
    def execute(self, job_info):

        _logger.info('Querying archive database...')
        rows = self._query_database()

        _logger.info('Performing output value substitutions...')
        rows = self._perform_substitutions(rows)

        _logger.info('Adding wildcard classification clip counts...')
        rows = self._add_wildcard_rows(rows)

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
    
    
    def _perform_substitutions(self, rows):
        return [self._perform_substitutions_aux(r) for r in rows]


    def _perform_substitutions_aux(self, r):
                
        classification = _CLASSIFICATION_SUBSTITUTIONS.get(
            r.classification, r.classification)
                    
        return _Row(
            r.detector, r.station, r.date, classification, r.clip_count)


    def _add_wildcard_rows(self, rows):

        parent_classifications = self._get_parent_classifications(rows)

        wildcard_rows = list(itertools.chain.from_iterable(
            self._create_wildcard_rows(rows, c)
            for c in parent_classifications))

        rows = rows + wildcard_rows

        rows.sort()

        return rows


    def _get_parent_classifications(self, rows):

        classifications = set()

        for r in rows:

            parts = r.classification.split('.')

            if len(parts) > 1:

                for i in range(len(parts) - 1):
                    classification = '.'.join(parts[:i + 1])
                    classifications.add(classification)

        return sorted(classifications)


    def _create_wildcard_rows(self, rows, parent_classification):


        # For each distinct combination of detector, station, and date,
        # count clips that have classifications that are subclassifications
        # of the parent classification, including the parent classification
        # itself.

        descendent_prefix = parent_classification + '.'
        clip_counts = defaultdict(int)

        for r in rows:

            classification = r.classification

            if classification == parent_classification or \
                    classification.startswith(descendent_prefix):

                key = (r.detector, r.station, r.date)
                clip_counts[key] += int(r.clip_count)
                

        # Create wildcard row for each clip count.
        wildcard_rows = [
            self._create_wildcard_row(key, clip_count, parent_classification)
            for key, clip_count in clip_counts.items()]
        
        return wildcard_rows


    def _create_wildcard_row(self, key, clip_count, parent_classification):
        t = key + (parent_classification + '*', clip_count)
        return _Row(*t)


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
        try:
            writer.writerow(_CSV_FILE_HEADER)
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
