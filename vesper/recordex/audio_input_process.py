import logging

from vesper.recordex.recorder_subprocess import RecorderSubprocess


_logger = logging.getLogger(__name__)


class AudioInputProcess(RecorderSubprocess):


    def __init__(self, settings, context):
        super().__init__('Audio Input', settings, context)


    def _init(self):
        _logger.info('AudioInputProcess._init')


    def _do_start_recording(self, command):
        _logger.info('AudioInputProcess._do_start_recording')


    def _do_stop_recording(self, command):
        _logger.info('AudioInputProcess._do_stop_recording')


    def _stop(self):
        _logger.info('AudioInputProcess._stop')
