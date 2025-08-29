import logging

from vesper.recordex.recorder_subprocess import RecorderSubprocess


_logger = logging.getLogger(__name__)


class AudioProcessingProcess(RecorderSubprocess):


    def __init__(self, settings, context):
        super().__init__('Audio Processing', settings, context)


    def _init(self):
        _logger.info('Audio processing process initializing.')


    def _do_process_audio(self, command):
        _logger.info(
            'Audio processing process received "process_audio" command.')


    def _stop(self):
        _logger.info('Audio processing process stopping.')
