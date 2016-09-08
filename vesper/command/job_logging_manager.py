"""Module containing class `JobLoggingManager`."""


from logging import FileHandler, Formatter, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
import logging
import os

import vesper.util.os_utils as os_utils


class JobLoggingManager:
    
    """
    Manages logging for a Vesper job.
    
    A `JobLoggingManager` manages logging for the processes of a Vesper job.
    Log records can be submitted by any process of a job using a logger
    created with the `create_logger` static method. These records are
    delivered via a multiprocessing queue to a thread running in the main
    job process, which writes corresponding messages to the job's log file.
    """
    
    
    @staticmethod
    def create_logger(logging_info):
        
        """
        Creates a logger for this job process.
        
        For the `logging_info` argument, the main job process can pass
        the `logging_info` attribute of its `JobLoggingManager`. This
        information is also passed to the `execute` method of the
        job's command as the `logging_info` attribute of the command's
        execution context. The information is picklable, so it can be
        delivered easily to any additional process started by the main
        job process as an argument to the process's target function.
        """
        
        job_id, level, queue = logging_info
        
        logger_name = 'Job {}'.format(job_id)
        logger = logging.getLogger(logger_name)
        
        logger.setLevel(level)
        
        handler = QueueHandler(queue)
        logger.addHandler(handler)
        
        return logger

    
    def __init__(self, job, level):
        
        self.job = job
        self.level = level
        
        # Create queue through which log records can be sent from various
        # processes and threads to the logging thread.
        self.queue = Queue()
        
        formatter = Formatter('%(asctime)s %(levelname)-8s %(message)s')
        
        # Create handler that writes log messages to the job log file.
        _create_parent_dir_if_needed(job.log_file_path)
        file_handler = FileHandler(job.log_file_path, 'w')
        file_handler.setFormatter(formatter)
        
        # Create handler that writes log messages to stderr.
        stderr_handler = StreamHandler()
        stderr_handler.setFormatter(formatter)
        
        self._handlers = (file_handler, stderr_handler)
        
        # Create logging listener that will run on its own thread and log
        # messages sent to it via the queue.
        self._listener = QueueListener(self.queue, *self._handlers)
        
        
    @property
    def logging_info(self):
        return (self.job.id, self.level, self.queue)
    
    
    def start_up_logging(self):
        self._listener.start()
        
        
    def shut_down_logging(self):
        
        # Tell logging listener to terminate, and wait for it to do so.
        self._listener.stop()
        
        logging.shutdown()


def _create_parent_dir_if_needed(file_path):
    dir_path = os.path.dirname(file_path)
    os_utils.create_directory(dir_path)
