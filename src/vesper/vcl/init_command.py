"""Module containing class `InitCommand`."""


import os

import yaml

from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.station import Station
from vesper.vcl.command import (
    Command, CommandSyntaxError, CommandExecutionError)
import vesper.util.vcl_utils as vcl_utils


class InitCommand(Command):
    
    """vcl command that creates a new archive."""
    
    
    name = 'init'
    
    
    # TODO: Make YAML file optional and specify it via a keyword
    # argument rather than a positional argument.
    
    
    def __init__(self, positional_args, keyword_args):
        
        super(InitCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        self._yaml_file_path = positional_args[0]
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        
        
    def execute(self):
        archive_data = _read_yaml_data(self._yaml_file_path)
        vcl_utils.create_archive(self._archive_dir_path, *archive_data)
        return True
    
    
def _read_yaml_data(file_path):
    
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

