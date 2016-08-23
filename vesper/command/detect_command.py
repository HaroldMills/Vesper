"""Module containing class `DetectCommand`."""


import itertools

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Recording, Station
import vesper.command.command_utils as command_utils


class DetectCommand(Command):
    
    
    extension_name = 'detect'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, context):
        
        self._logger = context.job.logger
        info = self._logger.info
        
        info('detectors: {}'.format(str(self._detector_names)))
        info('stations: {}'.format(str(self._station_names)))
        info('start date: {}'.format(str(self._start_date)))
        info('end date: {}'.format(str(self._end_date)))
        
        try:
            recordings = self._get_recordings()
            
        except Exception as e:
            self._logger.error((
                'Collection of recordings to run detector(s) on failed with '
                    'an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise
        
        info('recordings:')
        for recording in recordings:
            info('    {}'.format(str(recording)))

        return True
    
    
    def _get_recordings(self):
        return itertools.chain.from_iterable(
            self._get_station_recordings(
                name, self._start_date, self._end_date)
            for name in self._station_names)
            
            
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
            station_recorder__station=station,
            start_time__range=time_interval)
