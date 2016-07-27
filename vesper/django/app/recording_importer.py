"""Module containing `RecordingImporter` class."""


import itertools
import os

from django.db import transaction

from vesper.django.app.command import CommandExecutionError
from vesper.singletons import extension_manager, preset_manager
import vesper.django.app.command_utils as command_utils
import vesper.django.app.recording_utils as recording_utils
import vesper.util.audio_file_utils as audio_file_utils


class RecordingImporter(object):
    
    
    name = 'Recording Importer'
    
    
    def __init__(self, args):
        self.paths = command_utils.get_required_arg('paths', args)
        self.recursive = command_utils.get_optional_arg('recursive', args, True)
        spec = command_utils.get_optional_arg('recording_file_parser', args)
        self.file_parser = _create_file_parser(spec)
    
    
    def execute(self, context):
        
        self._logger = context.job.logger
        
        try:
            recordings = self._get_recordings()
            self._log_recordings(recordings)
            with transaction.atomic():
                self._add_recordings(recordings)
            
        except Exception as e:
            self._logger.error((
                'Recording import failed with an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

        return True
            
            
    def _get_recordings(self):
        files = list(itertools.chain.from_iterable(
            self._get_path_recording_files(path) for path in self.paths))
        return recording_utils.group_recording_files(files)

                
    def _get_path_recording_files(self, path):
        
        if os.path.isdir(path):
            return self._get_dir_recording_files(path)
        
        else:
            file = self._get_recording_file(path)
            return [] if file is None else [file]


    def _get_dir_recording_files(self, path):
        
        files = []
            
        for (dir_path, dir_names, file_names) in os.walk(path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                file = self._get_recording_file(file_path)
                if file is not None:
                    files.append(file)
                
            if not self.recursive:
                
                # Stop `os.walk` from descending into subdirectories.
                del dir_names[:]
                
        return files
                
                
    def _get_recording_file(self, file_path):
        
        if not audio_file_utils.is_wave_file_path(file_path):
            return None
        
        else:
            
            try:
                return self.file_parser.parse_file(file_path)
            
            except ValueError as e:
                raise CommandExecutionError(
                    'Error parsing recording file "{}": {}'.format(
                        file_path, str(e)))
            
    
    def _log_recordings(self, recordings):
        
        log = self._logger.info
        log('recordings:')
        for r in recordings:
            log('    {} {} {} {} {}'.format(
                r.station.name, r.num_channels, r.length,
                r.sample_rate, str(r.start_time)))
            for f in r.files:
                log('        {} {} {} {} {} {}'.format(
                    f.file_path, f.station.name, f.num_channels, f.length,
                    f.sample_rate, str(f.start_time)))


    def _add_recordings(self, recordings):
        pass
    
#         for r in recordings:
#             
#             station = Station.objects.get(name=r.station_name)
#             start_time = station.local_to_utc(r.start_time)
#             end_time = station.local_to_utc(r.end_time)
#             recording = Recording(
#                 station_recorder = None,
#                 num_channels = r.num_channels,
#                 length = r.length,
#                 sample_rate = r.sample_rate,
#                 start_time = start_time,
#                 end_time = end_time)
#             recording.save()
            
            
def _create_file_parser(spec):
    
    # Get station name aliases.
    parser_classes = \
        extension_manager.instance.get_extensions('Recording File Parser')
    parser_class = parser_classes[spec['name']]
    args = spec.get('arguments', {})
    preset_name = args['station_name_aliases_preset']
    preset = \
        preset_manager.instance.get_preset('Station Name Aliases', preset_name)
    station_name_aliases = preset.data
    
    return parser_class(station_name_aliases)
