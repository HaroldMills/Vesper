"""Base class for recorder subprocesses."""


from logging.handlers import QueueHandler
import logging

from vesper.recordex.recorder_process import RecorderProcess


class RecorderSubprocess(RecorderProcess):


    def __init__(self, name, settings, context):
        super().__init__(name=name)
        self._settings = settings
        self._context = context
        

    def _set_up_logging(self):
        
        """
        Set up logging for this recorder subprocess.

        This method sets up logging according to the `logging_level`
        and `logging_queue` attributes of the subprocess's `context`
        property.
        """

        # Get root logger for this process.
        logger = logging.getLogger()

        # Set logging level for this process.
        logger.setLevel(self._context.logging_level)

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        self._logging_queue_handler = QueueHandler(self._context.logging_queue)
        logger.addHandler(self._logging_queue_handler)


    def _tear_down_logging(self):

        """
        Tear down logging for this recorder subprocess.

        The code in this function is modeled after code suggested by
        ChatGPT 5. See notes towards top of `main_process.py`.
        """

        # Get root logger for this process.
        logger = logging.getLogger()

        try:

            # Close logging queue handler.
            handler = self._logging_queue_handler
            logger.removeHandler(handler)
            handler.close()

        finally:

            # Close this process's handle to logging queue so feeder
            # thread exits.
            queue = self._context.logging_queue
            queue.close()
            queue.join_thread()

