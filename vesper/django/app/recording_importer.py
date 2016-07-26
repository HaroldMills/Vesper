import itertools
import os

from django.db import transaction

from vesper.singletons import extension_manager
import vesper.django.app.command_utils as command_utils


class RecordingImporter(object):
    
    
    name = 'Recording Importer'
    
    
    def __init__(self, args):
        self.paths = command_utils.get_required_arg('paths', args)
        self.recursive = command_utils.get_optional_arg('recursive', args, True)
#         spec = command_utils.get_optional_arg('recording_file_parser', args)
#         self.recording_file_parser = _create_recording_file_parser(spec)
    
    
    def execute(self, context):
        
        self._logger = context.job.logger
        
        try:
            with transaction.atomic():
                self._add_recordings(self.paths, self.recursive)
                
        except Exception:
            self._logger.error(
                'Recording import failed with an exception. Database '
                'has been restored to its state before the import. See '
                'below for exception traceback.')
            raise
        
        return True
            
            
    def _add_recordings(self, paths, recursive):
        
        recordings = _get_recordings(paths, recursive)
        
        self._logger.info('recordings:')
        for recording in recordings:
            self._logger.info('    ' + recording)
                

def _create_recording_file_parser(spec):
    parser_classes = extension_manager.get_extensions('Recording File Parser')
    parser_class = parser_classes[spec['name']]
    args = spec.get('arguments', {})
    return parser_class(**args)
    
    
def _get_recordings(paths, recursive):
    recordings = list(itertools.chain.from_iterable(
        _get_path_recordings(path, recursive) for path in paths))
    return _merge_recordings(recordings)


def _get_path_recordings(path, recursive):
    
    if os.path.isdir(path):
        return _get_dir_recordings(path, recursive)
    
    else:
        return _create_recording(path)
    
    
def _get_dir_recordings(path, recursive):
    
    recordings = []
        
    for (dir_path, dir_names, file_names) in os.walk(path):
        
        for file_name in file_names:
            file_path = os.path.join(dir_path, file_name)
            recording = _create_recording(file_path)
            recordings.append(recording)
            
        if not recursive:
            
            # Stop `os.walk` from descending into subdirectories.
            del dir_names[:]
            
    return recordings
            
            
def _create_recording(file_path):
    # info = _get_file_info(file_path)
    return file_path


#     def _create_channel_recordings(self, file_path):
#         
#         info = self._input_file_parser.get_file_info(file_path)
#         
#         _check_sample_rate(info.sample_rate, file_path)
#             
#         recordings = []
#         
#         for channel_num, microphone_name in \
#                 enumerate(info.channel_microphone_names):
#             
#             if microphone_name is not None:
#                 
#                 station_name = info.station_name + ' ' + microphone_name
#                 
#                 # TODO: The following raises a `ValueError` if there
#                 # is no station with the specified name, for example if
#                 # the microphone name is unrecognized. Figure out how
#                 # best to deal with this. It might be better to do so
#                 # in the file parser rather than here.
#                 station = self._get_station(station_name)
#                 
#                 # Get UTC start time from local start time using station
#                 # time zone.
#                 t = info.start_time
#                 start_time = time_utils.create_utc_datetime(
#                     t.year, t.month, t.day, t.hour, t.minute, t.second,
#                     time_zone=station.time_zone)
#                     
#                 recording = Recording(
#                     station, start_time, info.length, info.sample_rate)
#                 recording.file_path = file_path
#                 recording.channel_num = channel_num
#                 recording.microphone_name = microphone_name
#                 
#                 recordings.append(recording)
#         
#         return recordings
# 
# 
# def _check_sample_rate(sample_rate, file_path):
#     if sample_rate != _INPUT_SAMPLE_RATE:
#         raise ValueError((
#             'Sample rate is {:g} Hz rather than the required {:d} Hz '
#             'for input sound file "{:s}".').format(
#                 sample_rate, _INPUT_SAMPLE_RATE, file_path))


def _merge_recordings(recordings):
    return recordings
            
    
