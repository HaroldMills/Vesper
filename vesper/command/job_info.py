"""Module containing class `JobInfo`."""


from vesper.command.job_logging_manager import JobLoggingManager


class JobInfo:
    
    """
    Job-related information useful during command execution.
    
    This information includes the following:
    
        job_id : `int`
            the ID of the Django model instance for this job.
            
            The ID of the Django model instance is included here rather
            than the instance itself so that an instance of this class
            can be unpickled in a new process without first setting up
            Django.
            
        logging_config : picklable object
            the logging configuration for this job.
            
            Each process of this job should configure its logger
            (typically the root logger) by invoking the
            `JobLoggingManager.configure_logger` static method exactly
            once with this configuration.
           
        stop_event : `multiprocessing.Event`
            event indicating job stop request.
            
            This event is set when it has been requested that this job
            stop without completing.
    """
    
    
    def __init__(self, job_id, logging_config, stop_event):
        self.job_id = job_id
        self._logging_config = logging_config
        self._stop_event = stop_event
        
        
    @property
    def stop_requested(self):
        return self._stop_event.is_set()
    
    
    def configure_logger(self, logger):
        JobLoggingManager.configure_logger(logger, self._logging_config)
