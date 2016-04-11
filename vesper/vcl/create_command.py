"""Module containing class `CreateCommand`."""


import os

import yaml

from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.station import Station
from vesper.vcl.command import Command, CommandExecutionError
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
create [<keyword arguments>]

Creates a new archive.
'''.strip()
        

# TODO: Document YAML file format, if only by example.

_ARGS = '''

- name: --archive
  required: false
  value description: directory path
  documentation: |
      The directory path of the new archive. If the directory exists it
      must not already contain an archive. If this argument is not
      provided, the new archive will be created in the current directory.
  
- name: --archive-data
  required: false
  value description: file path
  documentation: |
      The path of a YAML file containing data for the new archive. If
      this argument is not provided, the new archive will be empty.
      
'''


class CreateCommand(Command):
    
    """vcl command that creates a new archive."""
    
    
    name = 'create'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        arg_descriptors = vcl_utils.parse_command_args_yaml(_ARGS)
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return _HELP + '\n\n' + args_help
    
    
    def __init__(self, positional_args, keyword_args):
        super(CreateCommand, self).__init__()
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        self._yaml_file_path = \
            vcl_utils.get_optional_keyword_arg('archive-data', keyword_args)
        
        
    def execute(self):
        data = _get_archive_data(self._yaml_file_path)
        vcl_utils.create_archive(self._archive_dir_path, *data)
        return True
    
    
def _get_archive_data(file_path):
    
    if file_path is None:
        return ([], [], [])
    
    if not os.path.exists(file_path):
        raise CommandExecutionError(
            'YAML file "{:s}" not found.'.format(file_path))
        
    # TODO: Improve error reporting in the following.
    try:
        
        data = yaml.load(open(file_path, 'r').read())
        
        station_dicts = data.get('stations', [])
        detector_names = data.get('detectors', [])
        clip_class_names = data.get('clip_classes', [])
        
        # TODO: Validate station, detector, and clip class data.
        stations = [Station(**kwds) for kwds in station_dicts]
        detectors = [Detector(name) for name in detector_names]
        clip_classes = [ClipClass(name) for name in clip_class_names]
        
    except Exception as e:
        raise CommandExecutionError((
            'Error reading archive data from YAML file "{:s}": '
            '{:s}').format(file_path, str(e)))
    
    return stations, detectors, clip_classes
