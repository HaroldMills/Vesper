"""
Module containing class `ExportClipCountsByClassificationToCsvFileCommand`.
"""


from collections import namedtuple, defaultdict
import itertools
import logging

from django.db import connection

from vesper.command.command import Command
import vesper.command.command_utils as command_utils


# TODO: Allow user specification of sets of detectors, sensors, dates, and
#       annotation values of clips to count.
# TODO: Allow user specification of annotation name.
# TODO: Optionally output estimated bird counts as well as clip counts.
#       This will require looking at clip times.


_logger = logging.getLogger()


_ANNOTATION_NAME = 'Classification'

_ANNOTATION_VALUE_SUBSTITUTIONS = {
    None: 'Unclassified'
}

_ANNOTATION_VALUE_COMPONENT_SEPARATOR = '.'


def _create_clip_count_query(annotation_name):

    return f'''
SELECT
    vesper_processor.name AS detector_name,
    vesper_station.name AS station_name,
    vesper_clip.date AS date,
    vesper_string_annotation.value AS annotation_value,
    count(*)
FROM
    vesper_clip
LEFT JOIN vesper_string_annotation
    ON vesper_clip.id = vesper_string_annotation.clip_id
        AND info_id = (
            SELECT id from vesper_annotation_info
            WHERE name = '{annotation_name}')
INNER JOIN vesper_processor
    ON vesper_clip.creating_processor_id = vesper_processor.id
INNER JOIN vesper_station
    ON vesper_station.id = vesper_clip.station_id
GROUP BY
    detector_name,
    station_name,
    date,
    annotation_value
'''.lstrip()


def _get_csv_file_header(annotation_name):
    return ('Detector', 'Station', 'Date', annotation_name, 'Clips')


_Row = namedtuple(
    '_Row',
    ('detector_name', 'station_name', 'date', 'annotation_value',
     'clip_count'))


class ExportClipCountsByClassificationToCsvFileCommand(Command):
    
    
    extension_name = 'export_clip_counts_by_classification_to_csv_file'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._output_file_path = get('output_file_path', args)

        # In the future, these might come from the command arguments
        # and/or a preset named by a command argument.
        self._annotation_name = _ANNOTATION_NAME
        self._annotation_value_substitutions = _ANNOTATION_VALUE_SUBSTITUTIONS
        self._annotation_value_component_separator = \
            _ANNOTATION_VALUE_COMPONENT_SEPARATOR
        
        
    def execute(self, job_info):

        _logger.info('Querying archive database...')
        rows = self._query_database(self._annotation_name)

        _logger.info('Performing classification value substitutions...')
        rows = self._perform_substitutions(
            rows, self._annotation_value_substitutions)

        if self._annotation_value_component_separator is not None:
            _logger.info(
                'Adding clip counts for wildcard classification values...')
            rows = self._add_wildcard_rows(
                rows, self._annotation_value_component_separator)

        _logger.info('Writing output file...')
        header = _get_csv_file_header(self._annotation_name)
        command_utils.write_csv_file(self._output_file_path, rows, header)

        return True


    def _query_database(self, annotation_name):

        query = _create_clip_count_query(annotation_name)

        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        except Exception as e:
            command_utils.handle_command_execution_error(
                'Database query failed.', e)

        return [_Row(*r) for r in rows]


    def _perform_substitutions(self, rows, substitutions):
        return [
            self._perform_substitutions_aux(r, substitutions) for r in rows]


    def _perform_substitutions_aux(self, row, substitutions):
                
        value = substitutions.get(row.annotation_value)

        if value is None:
            return row

        else:
            return row._replace(annotation_value=value)


    def _add_wildcard_rows(self, rows, separator):

        parent_values = self._get_parent_annotation_values(rows, separator)

        wildcard_rows = list(itertools.chain.from_iterable(
            self._create_wildcard_rows(rows, v, separator)
            for v in parent_values))

        rows = rows + wildcard_rows

        rows.sort()

        return rows


    def _get_parent_annotation_values(self, rows, separator):

        parent_values = set()

        for r in rows:

            parts = r.annotation_value.split(separator)

            if len(parts) > 1:

                for i in range(len(parts) - 1):
                    parent_value = separator.join(parts[:i + 1])
                    parent_values.add(parent_value)

        return sorted(parent_values)


    def _create_wildcard_rows(self, rows, parent_annotation_value, separator):


        # For each distinct combination of detector, station, and date,
        # count clips that have annotation values that are subvalues
        # of the parent value, including the parent value itself.

        descendent_prefix = parent_annotation_value + separator
        clip_counts = defaultdict(int)

        for r in rows:

            value = r.annotation_value

            if value == parent_annotation_value or \
                    value.startswith(descendent_prefix):

                key = (r.detector_name, r.station_name, r.date)
                clip_counts[key] += int(r.clip_count)
                

        # Create wildcard row for each clip count.
        wildcard_rows = [
            self._create_wildcard_row(key, clip_count, parent_annotation_value)
            for key, clip_count in clip_counts.items()]
        
        return wildcard_rows


    def _create_wildcard_row(self, key, clip_count, parent_annotation_value):
        t = key + (parent_annotation_value + '*', clip_count)
        return _Row(*t)
