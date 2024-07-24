from logging import Formatter, FileHandler, StreamHandler
from multiprocessing import Process, Queue
import logging


class LoggingProcess(Process):

    """
    Process that logs all Vesper Recorder messages.
    
    There are multiple processes in the Vesper Recorder that need to
    log messages. Python logging handlers are not all multiprocess-safe,
    however, so all log messages are sent to this process by the other
    processes of the recorder for logging. Then, since there's only one
    process (i.e. this one) that does the actual logging, the result is
    multiprocess-safe.

    This class is inspired by code that appears in the *Logging to a
    single file from multiple processes* section of the Python Logging
    Cookbook (https://docs.python.org/3/howto/logging-cookbook.html#
    logging-to-a-single-file-from-multiple-processes).
    """


    def __init__(self, logging_level, log_file_path):
        super().__init__(name='Logging Process')
        self._level = logging_level
        self._log_file_path = log_file_path
        self._queue = Queue()


    @property
    def queue(self):
        return self._queue
    

    def run(self):

        self._configure_logging(self._level)

        while True:

            try:

                record = self._queue.get()

                if record is None:
                    # we're being told to stop

                    break

                logger = logging.getLogger(record.name)
                logger.handle(record)

            except Exception:
                import sys, traceback
                print('Logger encountered an error:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)


    def _configure_logging(self, level):
        
        # Create handler that writes log messages to stderr.
        stderr_handler = StreamHandler()
        formatter = Formatter('%(asctime)s %(levelname)s %(message)s')
        stderr_handler.setFormatter(formatter)
        
        # Create handler that appends messages to log file.
        file_handler = FileHandler(self._log_file_path)
        formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        # Add handlers to root logger.
        logger = logging.getLogger()
        logger.addHandler(stderr_handler)
        logger.addHandler(file_handler)
        
        # Set root logger level.
        logger.setLevel(level)
    

    def stop(self):
        self._queue.put_nowait(None)