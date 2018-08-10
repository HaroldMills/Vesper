"""Module containing class `JobLoggingManager`."""


from collections import defaultdict
from logging import FileHandler, Formatter, Handler, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
import logging

import vesper.util.os_utils as os_utils


# TODO: Add record count fields to the `Job` model class, and modify
# the record counts handler to update the fields both while a job is
# running and upon completion. 
class _RecordCountsHandler(Handler):
    
    def __init__(self):
        super().__init__()
        self.record_counts = defaultdict(int)
        
    def emit(self, record):
        self.record_counts[record.levelno] += 1
        
        
class JobLoggingManager:
    
    """
    Manages logging for a Vesper job.
    
    A `JobLoggingManager` manages logging for the processes of a Vesper job.
    Log records can be submitted by any process of a job using any logger
    (typically the root logger) configured with the `configure_logger`
    static method. A logger so configured writes each log record to a
    multiprocessing queue that is read by a thread running in the main
    job process, which in turn writes log messages to the job's log file.
    """
    
    
    @staticmethod
    def configure_logger(logger, logging_config):
        
        """
        Configures the specified logger to write log records to this job's
        logging queue.
        
        For the `logging_config` argument, the main job process can pass
        the `logging_config` attribute of its `JobLoggingManager`. This
        information is also passed to the `execute` method of the job's
        command as the `logging_config` attribute of the command's
        execution context. The information is picklable, so it can be
        delivered easily to any additional process started by the main
        job process as an argument to the process's target function.        
        """
        
        level, queue = logging_config
        
        logger.setLevel(level)
        
        handler = QueueHandler(queue)
        logger.addHandler(handler)

        
    def __init__(self, job, level):
        
        self.job = job
        self.level = level
        
        # Create queue through which log records can be sent from various
        # processes and threads to the logging thread.
        self.queue = Queue()
        
        formatter = Formatter('%(asctime)s %(levelname)-8s %(message)s')
        
        # Create handler that writes log messages to the job log file.
        os_utils.create_parent_directory(job.log_file_path)
        file_handler = FileHandler(job.log_file_path, 'w')
        file_handler.setFormatter(formatter)
        
        # Create handler that writes log messages to stderr.
        stderr_handler = StreamHandler()
        stderr_handler.setFormatter(formatter)
        
        self._record_counts_handler = _RecordCountsHandler()
        
        # Create logging listener that will run on its own thread and log
        # messages sent to it via the queue.
        self._listener = QueueListener(
            self.queue, file_handler, stderr_handler,
            self._record_counts_handler)
        
        
    @property
    def logging_config(self):
        return (self.level, self.queue)
    
    
    @property
    def record_counts(self):
        return dict(self._record_counts_handler.record_counts)
    
    
    def start_up_logging(self):
        self._listener.start()
        
        
    def shut_down_logging(self):
        
        # Tell logging listener to terminate, and wait for it to do so.
        self._listener.stop()
        
        logging.shutdown()
