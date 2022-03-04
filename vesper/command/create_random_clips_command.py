"""Module containing class `CreateRandomClipsCommand`."""


import logging

from vesper.command.command import Command
from vesper.singleton.archive import archive
from vesper.singleton.preset_manager import preset_manager
import vesper.command.command_utils as command_utils


class CreateRandomClipsCommand(Command):
    
    
    extension_name = 'create_random_clips'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._schedule_name = get('schedule', args)
        self._clip_duration = get('clip_duration', args)
        self._clip_count = get('clip_count', args)
        
        self._schedule = _get_schedule(self._schedule_name)
        self._station_schedules = {}
        
        
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()

        self._logger.info('CreateRandomClipsCommand.execute')

        return True
    

def _get_schedule(schedule_name):
    
    if schedule_name == archive.NULL_CHOICE:
        # no schedule specified

        return None
    
    else:
        # schedule specified
        
        preset_path = ('Detection Schedule', schedule_name)
        preset = preset_manager.get_preset(preset_path)
        return preset.data
