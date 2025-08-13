"""Base class for recorder processes."""


from logging.handlers import QueueHandler
import logging
import multiprocessing as mp
import queue

from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


class RecorderProcess(mp.Process):


    def __init__(self, name, settings, context):

        super().__init__(name=name)

        self._settings = settings
        self._context = context
        self._command_queue = mp.Queue()
        self._stop_event = mp.Event()


    def run(self):

        self._configure_logging()

        self._init()

        while not self._stop_event.is_set():

            try:
                command = self._command_queue.get(timeout=1)
            except queue.Empty:
                continue

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

        self._stop()
        

    def _configure_logging(self):
        
        """
        Configures logging for this process.

        This method configures logging according to the `logging_level`
        and `logging_queue` attributes of the process's `context` property.
        """

        # Get the root logger for this process.
        logger = logging.getLogger()

        # Set logging level for this process.
        logger.setLevel(self._context.logging_level)

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        handler = QueueHandler(self._context.logging_queue)
        logger.addHandler(handler)


    def _init(self):
        pass


    def start_recording(self):
        command = Bunch(name='start_recording')
        self._command_queue.put(command)


    def stop_recording(self):
        command = Bunch(name='stop_recording')
        self._command_queue.put(command)


    def stop(self):
        self._stop_event.set()


    def _do_start_recording(self, command):
        pass


    def _do_stop_recording(self, command):
        pass


    def _stop(self):
        pass
