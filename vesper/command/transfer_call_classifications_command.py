"""Module containing class `TransferCallClassificationsCommand`."""


import logging

from vesper.command.command import Command
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils


'''
Transfer call classifications from clips of one detector to clips of another.

Arguments:
* source detector
* target detector
* station/mic output pairs
* start date
* end date

The command will support only detectors for which call start times are
within a known window.

For each recording of the specified station/mics and dates, the command will
match call clips of the source detector with unclassified clips of the target
detector, and classify the target detector clips accordingly.

The matching algorithm will match a source detector call clip with a target
detector clip if their call start windows intersect. A source detector call
clip's call start window intersects the call start window of a target
detector clip if and only if the center of the call clip's window is within
a window with the same center as the target detector clip's call start window,
and whose width is the maximum of the call start window widths of the two
detectors. Thus we can use the same matching code we use to evaluate
detectors on the BirdVox-full-night recordings to perform the transfer
matching.
'''


_logger = logging.getLogger()


class TransferCallClassificationsCommand(Command):
    
    
    extension_name = 'transfer_call_classifications'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._source_detector_name = get('source_detector', args)
        self._target_detector_name = get('target_detector', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, job_info):
        
        self._job_info = job_info

        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', 'Call*')

        self._transfer_classifications()
        
        return True
    
    
    def _transfer_classifications(self):
        
        value_tuples = self._create_clip_query_values_iterator()
        
        for detector, station, mic_output, date in value_tuples:
            _logger.info('{} / {} / {} / {}'.format(
                detector.name, station.name, mic_output.name, str(date)))
            

    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                [self._source_detector_name], self._sm_pair_ui_names,
                self._start_date, self._end_date)
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction',
                'The archive was not modified.')
