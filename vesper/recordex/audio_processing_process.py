# This import should precede all others.
import vesper.recordex.keyboard_interrupt_disabler

import logging

from vesper.recordex.subprocess import Subprocess


_logger = logging.getLogger(__name__)


class AudioProcessingProcess(Subprocess):


    def __init__(self, settings, logging_level, logging_queue):
        super().__init__(
            'AudioProcessingProcess', settings, logging_level, logging_queue)


    def _do_process_audio(self, command):
        # _logger.info(
        #     'Audio processing process received "process_audio" command.')
        pass


    def _stop(self):
        _logger.info('Audio processing process stopping...')
