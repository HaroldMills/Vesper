"""Base class for subprocesses of recorder main process."""


from logging.handlers import QueueHandler
import logging

from vesper.recordex.recorder_process import RecorderProcess


class RecorderSubprocess(RecorderProcess):


    def __init__(self, name, settings, context):

        super().__init__(name=name)

        self._settings = settings
        self._context = context

        # The `self._logging_queue` attribute is required by the
        # default implementation of the `RecorderProcess._stop_logging`
        # method.
        self._logging_queue = context.logging_queue
        

    def _start_logging(self):
        
        """
        Start logging for this recorder subprocess.

        This method starts logging according to the `logging_level`
        and `logging_queue` attributes of the subprocess's `context`
        property.
        """

        # Get root logger for this process.
        logger = logging.getLogger()

        # Set logging level for this process.
        logger.setLevel(self._context.logging_level)

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        self._logging_queue_handler = QueueHandler(self._logging_queue)
        logger.addHandler(self._logging_queue_handler)
