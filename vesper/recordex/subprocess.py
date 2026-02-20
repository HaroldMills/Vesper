"""Base class for subprocesses of recorder main process."""


from logging.handlers import QueueHandler
import logging

from vesper.recordex.process import Process


class Subprocess(Process):


    def __init__(self, name, settings, logging_level, logging_queue):
        super().__init__(name=name)
        self._settings = settings
        self._logging_level = logging_level
        self._logging_queue = logging_queue
        

    def _start_logging(self):
        
        """Start logging for this recorder subprocess."""

        # Get root logger for this process.
        logger = logging.getLogger()

        # Set logging level for this process.
        logger.setLevel(self._logging_level)

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        self._logging_queue_handler = QueueHandler(self._logging_queue)
        logger.addHandler(self._logging_queue_handler)
