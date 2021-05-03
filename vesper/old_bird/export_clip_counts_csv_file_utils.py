"""Module containing class `ClipCountsExporter`."""


import csv
import datetime

from vesper.singleton.archive import archive
import vesper.django.app.model_utils as model_utils
import vesper.old_bird.clip_count_utils as clip_count_utils


'''
Clip Count Table preset for Old Bird:

preset_type: Clip Count Table
preset_type_version: 1.0

default_annotation_name: Classification

columns:
    - Call*
    - Call.AMRE
    - Call.BAWW
    - Call.BTBW
    - Call.CAWA
    - Call.CMWA
    - Call.COYE
    - Call.CSWA
    - Call.DbUp
    - Call.HOWA
    - Call.MOWA
    - Call.NOPA
    - Call.NWTH
    - Call.OVEN
    - Call.SVSP
    - Call.WIWA
    - Call.Zeep
    
annotation_value_prefixes_hidden_in_column_names: [Call.]

include_column_totals: false

bird_counts:
    annotation_value_prefixes: [Call.]
    count_suppression_interval: 60



Another Clip Count Table preset:

preset_type: Clip Count Table
preset_type_version: 1.0

default_annotation_name: Classification

columns:

    - type: Total Clip Count

    # Here is an example of using a dictionary instead of a string to
    # specify an annotated clip count column.
    - type: Annotated Clip Count
      annotation_value: Call*
      
    # Note that we will want to name this column "Call.*" even though
    # we specify below that the annotation value prefix "Call." should
    # hidden in column names. In general, we don't hide a prefix for
    # an annotation value "<prefix>*".
    - Call.*
    - Noise
    - Tone
    
    - type: Unannotated Clip Count
      name: Unclassified
    
annotation_value_prefixes_hidden_in_column_names: [Call.]

include_column_totals: true

bird_count:
    annotation_value_prefixes: [Call.]
    count_suppression_interval: 60



If no columns are specified in a Clip Count Table preset, we create a
column for each annotation value of the system.
'''


_ANNOTATION_NAME = 'Classification'

_ANNOTATION_VALUES = (
    'Call*',
    'Call.AMRE',
    'Call.BAWW',
    'Call.BTBW',
    'Call.CAWA',
    'Call.CMWA',
    'Call.COYE',
    'Call.CSWA',
    'Call.DbUp',
    'Call.HOWA',
    'Call.MOWA',
    'Call.NOPA',
    'Call.NWTH',
    'Call.OVEN',
    'Call.SVSP',
    'Call.WIWA',
    'Call.Zeep'
)

_CALL_TYPE_PREFIX = 'Call.'

_BIRD_COUNT_SUPPRESSION_INTERVAL = 60    # seconds

_ONE_DAY = datetime.timedelta(days=1)


def get_clip_counts_csv_file_name(
        file_name, detector_name, station_mic_ui_name, start_date, end_date):
    
    file_name = file_name.strip()
    
    if len(file_name) != 0:
        return file_name
    
    else:
        
        # In the interest of simplicity over specificity, we include
        # only the station name and the start and end dates in our
        # automatically-generated CSV file names.
        
        sm_pairs_dict = model_utils.get_station_mic_output_pairs_dict()
        station, _ = sm_pairs_dict[station_mic_ui_name]
        
        file_name = 'Clip Counts_{}_{}_{}.csv'.format(
            station.name, start_date, end_date)
        
        return file_name
    
    
def write_clip_counts_csv_file(
        file_, detector_name, station_mic_ui_name, start_date, end_date):
    
    detector = archive.get_processor(detector_name)
    
    sm_pairs_dict = model_utils.get_station_mic_output_pairs_dict()
    station, mic_output = sm_pairs_dict[station_mic_ui_name]
    
    bird_count_suppression_interval = \
        datetime.timedelta(seconds=_BIRD_COUNT_SUPPRESSION_INTERVAL)
    
    clip_counts = _get_clip_counts(
        station, mic_output, detector, start_date, end_date,
        _ANNOTATION_NAME, _ANNOTATION_VALUES)
    
    bird_counts = _get_bird_counts(
        station, mic_output, detector, start_date, end_date,
        _ANNOTATION_NAME, _ANNOTATION_VALUES,
        bird_count_suppression_interval)
    
    _write_file(
        file_, start_date, end_date, _ANNOTATION_VALUES, clip_counts,
        bird_counts)
        
           
def _get_clip_counts(
        station, mic_output, detector, start_date, end_date,
        annotation_name, annotation_values):
    
    counts = {}
    
    for annotation_value in annotation_values:
        
        value_counts = model_utils.get_clip_counts(
            station, mic_output, detector, annotation_name,
            annotation_value)
        
        for date, count in value_counts.items():
            counts[(date, annotation_value)] = count
            
    return counts
                
               
def _get_bird_counts(
        station, mic_output, detector, start_date, end_date,
        annotation_name, annotation_values, count_suppression_interval):
    
    counts = {}
    
    for annotation_value in annotation_values:
        
        if _is_call_type(annotation_value):
            
            for date in _date_range(start_date, end_date):
                
                clips = model_utils.get_clips(
                    station=station,
                    mic_output=mic_output,
                    date=date,
                    detector=detector,
                    annotation_name=annotation_name,
                    annotation_value=annotation_value)
                
                times = sorted(c.start_time for c in clips)
                
                count = clip_count_utils.get_bird_count(
                    times, count_suppression_interval)
        
                counts[(date, annotation_value)] = count
            
    return counts


def _is_call_type(annotation_value):
    return annotation_value.startswith(_CALL_TYPE_PREFIX) and \
        not annotation_value.endswith('*')


def _date_range(start_date, end_date):
    date = start_date
    while date <= end_date:
        yield date
        date += _ONE_DAY


def _write_file(
        file_, start_date, end_date, annotation_values, clip_counts,
        bird_counts):
    
    writer = csv.writer(file_)
    
    _write_header(writer, annotation_values)
    
    for date in _date_range(start_date, end_date):
        _write_row(writer, date, annotation_values, clip_counts, bird_counts)

           
def _write_header(writer, annotation_values):
    column_names = ['Date'] + [_get_column_name(v) for v in annotation_values]
    writer.writerow(column_names)


def _get_column_name(annotation_value):
    if _is_call_type(annotation_value):
        return annotation_value[len(_CALL_TYPE_PREFIX):]
    else:
        return annotation_value
    
    
def _write_row(writer, date, annotation_values, clip_counts, bird_counts):
    
    count_strings = [
        _get_count_string(date, value, clip_counts, bird_counts)
        for value in annotation_values]
    
    writer.writerow([str(date)] + count_strings)


def _get_count_string(date, annotation_value, clip_counts, bird_counts):
    
    key = (date, annotation_value)
    
    clip_count = clip_counts.get(key)
    
    if clip_count is not None:
        
        count_string = str(clip_count)
        
        if _is_call_type(annotation_value):
            
            bird_count = bird_counts[key]
            
            if bird_count != clip_count:
                count_string += '({})'.format(bird_count)
                
    else:
        # no clip count
        
        count_string = ''
        
    return count_string
