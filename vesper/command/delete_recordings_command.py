"""Module containing class `DeleteRecordingsCommand`."""


import itertools
import logging

from django.db import transaction

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Clip, Recording, Station
from vesper.singleton.clip_manager import clip_manager
import vesper.command.command_utils as command_utils
import vesper.util.archive_lock as archive_lock


class DeleteRecordingsCommand(Command):
    
    
    extension_name = 'delete_recordings'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()

        recordings = self._get_recordings()  
        self._delete_recordings(recordings)
            
        return True
    
    
    def _get_recordings(self):
        
        try:
            return list(itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names))
            
        except Exception as e:
            self._logger.error((
                'Collection of recordings to delete failed with an '
                    'exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

            
    def _get_station_recordings(self, station_name, start_date, end_date):

        # TODO: Test behavior for an unrecognized station name.
        # I tried this on 2016-08-23 and got results that did not
        # make sense to me. An exception was raised, but it appeared
        # to be  raised from within code that followed the except clause
        # in the `execute` method above (the code logged the sequence of
        # recordings returned by the `_get_recordings` method) rather
        # than from within that clause, and the error message that I
        # expected to be logged by that clause did not appear in the log.
        
        try:
            station = Station.objects.get(name=station_name)
        except Station.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized station "{}".'.format(station_name))
        
        time_interval = station.get_night_interval_utc(start_date, end_date)
        
        return Recording.objects.filter(
            station=station,
            start_time__range=time_interval)


    def _delete_recordings(self, recordings):
        
        for recording in recordings:
            
            try:
                self._delete_recording(recording)
                
            except Exception as e:
                self._logger.error((
                    'Deletion of recording "{}" failed with an exception.\n'
                    'The exception message was:\n'
                    '    {}\n'
                    'The recording and associated clips and annotations '
                    'were not modified.\n'
                    'See below for exception traceback.').format(str(e)))
                raise


    def _delete_recording(self, recording):
        
        self._logger.info('Deleting recording "{}"...'.format(str(recording)))
        
        with archive_lock.atomic():
            
            with transaction.atomic():
            
                # TODO: Consider moving file deletions outside of database
                # transaction.
                
                clips = Clip.objects.filter(
                    recording_channel__recording=recording)
                
                # Delete clip files.
                for clip in clips:
                    clip_manager.delete_audio_file(clip)
                
                recording.delete()
