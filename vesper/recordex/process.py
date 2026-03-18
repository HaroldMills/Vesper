"""
Base class for all recorder processes other than the main process.
"""


from logging.handlers import QueueHandler
import logging
import multiprocessing as mp
import queue

from vesper.recordex.lifecycle_executor import LifecycleExecutor
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


# TODO: Consider adding initializer argument that controls whether or not
# initializer creates a multiprocessing command queue, a multithreading
# command queue, or no command queue.


class Process(mp.Process):


    def __init__(self, name, settings, logging_level, logging_queue):

        super().__init__(name=name)

        self._settings = settings
        self._logging_level = logging_level
        self._logging_queue = logging_queue

        self._stop_event = mp.Event()
        self._command_queue = mp.Queue()


    @property
    def stop_event(self):
        return self._stop_event


    @property
    def command_queue(self):
        return self._command_queue


    def run(self):

        lifecycle = (
            ('_start_logging', None, None),
            ('_start', _logger, '_stop_logging'),
            ('_run', _logger, '_stop'),
            ('_stop', _logger, '_stop_logging'),
            ('_stop_logging', None, None))
        
        executor = LifecycleExecutor(self, self.name, lifecycle)
        executor.execute_lifecycle()


    def _start_logging(self):

        # Get root logger for this process.
        logger = logging.getLogger()

        # Set logging level for this process.
        logger.setLevel(self._logging_level)

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        self._logging_queue_handler = QueueHandler(self._logging_queue)
        logger.addHandler(self._logging_queue_handler)


    def _start(self):
        pass


    def _run(self):

        while not self._stop_event.is_set():

            try:
                command = self._command_queue.get(timeout=1)
            except queue.Empty:
                continue

            # For convenience, allow commands that have no arguments to
            # be enqueued as strings.
            if isinstance(command, str):
                command = Bunch(name=command)

            method_name = f'_do_{command.name}'

            try:
                method = getattr(self, method_name)
            except AttributeError:
                _logger.warning(f'Unrecognized command "{command.name}".')
                continue

            try:
                method(command)
            except Exception as e:
                _logger.warning(
                    f'Error executing command "{command.name}". '
                    f'Exception message was: {e}')


    def _stop(self):
        pass


    def _stop_logging(self):

        # Close logging queue handler.
        logger = logging.getLogger()
        handler = self._logging_queue_handler
        logger.removeHandler(handler)
        handler.close()

        # Close this process's handle to logging queue and wait for
        # queue feeder thread to exit.
        queue = self._logging_queue
        queue.close()
        queue.join_thread()
