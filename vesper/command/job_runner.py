"""
Module containing function that runs a Vesper job.

The `run_job` function runs in a new process for each job that Vesper
executes. The new process is called the *main job process* for the job.
The `run_job` function is in its own module rather than in the `job_manager
module in order to minimize the number of imports that the module containing
the function, and hence the new process, must perform.
"""


import logging
import pprint
import traceback

from vesper.command.command import CommandSyntaxError
from vesper.command.job_logging_manager import JobLoggingManager
import vesper.util.django_utils as django_utils
import vesper.util.time_utils as time_utils


'''
Job status values:

Not Started
Running
Complete
Interrupted
Raised Exception
'''


def run_job(job_info):
    
    # Set up Django for the main job process. We must do this before we try
    # to use anything Django (e.g. the ORM) in the new process. We perform
    # the setup inside of this function rather than at the top of this module
    # so that it happens only in a new job process, and not in a parent
    # process that is importing this module merely to be able to execute
    # this function. In the latter case Django will already have been set up
    # in the importing process if it is needed, and it would be redundant
    # and potentially problematic to perform the setup again.
    django_utils.set_up_django()
    
    # These imports are here rather than at the top of this module so
    # they will be executed after Django is set up in the main job process.
    from django.conf import settings as django_settings
    from vesper.django.app.models import Job

    # Get the Django model instance for this job.
    job = Job.objects.get(id=job_info.job_id)
    
    # Start up logging.
    level = logging.DEBUG if django_settings.DEBUG else logging.INFO
    logging_manager = JobLoggingManager(job, level)
    logging_manager.start_up_logging()
    
    # Create logger for the main job process.
    logging_info = logging_manager.logging_info
    logger = JobLoggingManager.create_logger(logging_info)
    
    try:
        
        # Mark job as running.
        job.start_time = time_utils.get_utc_now()
        job.status = 'Running'
        job.save()
        
        # Create command from command spec.
        command = _create_command(job_info.command_spec)
        
        # Log start message.
        command_args = pprint.pformat(command.arguments, indent=1)
        command_args = _indent_lines(command_args, 4)
        logger.info(
            'Job started for command "{}" with arguments:\n{}'.format(
                command.name, command_args))
    
        # Execute command.
        context = _CommandExecutionContext(
            job, logger, logging_info, job_info.stop_event)
        complete = command.execute(context)
        
    except Exception:
        
        # Update job status and log error message
        job.end_time = time_utils.get_utc_now()
        job.status = 'Raised Exception'
        job.save()
        logger.error('Job raised exception.\n' + traceback.format_exc())
        
    else:
        
        # Update job status and log completion or interruption message.
        
        job.end_time = time_utils.get_utc_now()
        
        if complete:
            job.status = 'Complete'
            log_message = 'Job complete.'
            
        else:
            job.status = 'Interrupted'
            log_message = 'Job interrupted.'
            
        job.save()
        logger.info(log_message)
        
    finally:
        logging_manager.shut_down_logging()


def _create_command(command_spec):

    try:
        command_name = command_spec['name']
    except KeyError:
        raise CommandSyntaxError(
            'Command specification contains no "name" item.')
        
    # We put this here to avoid a circular import problem.
    from vesper.singletons import extension_manager
    
    command_classes = extension_manager.instance.get_extensions('Command')
    
    try:
        command_class = command_classes[command_name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized command "{}".'.format(command_name))
        
    command_args = command_spec.get('arguments', {})
    
    return command_class(command_args)


def _indent_lines(text, num_spaces):
    prefix = ' ' * num_spaces
    lines = text.split('\n')
    indented_lines = [prefix + line for line in lines]
    return '\n'.join(indented_lines)


class _CommandExecutionContext:
    
    """
    Job-related information useful during command execution.
    
    This information includes the following attributes:
    
        job : the Django model instance for the job
        
        logger : a logger for use by the main job process
        
        logging_info : a picklable object from which subprocesses of the
            main job process can create loggers via the
            `JobLoggingManager.create_logger` static method.
            
        stop_requested : `True` if and only if it has been requested
            that command execution stop without completing.
    """
    
    def __init__(self, job, logger, logging_info, stop_event):
        self.job = job
        self.logger = logger
        self.logging_info = logging_info
        self._stop_event = stop_event
        
    @property
    def stop_requested(self):
        return self._stop_event.is_set()
