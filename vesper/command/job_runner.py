"""
Module containing function that runs a Vesper job.

The `run_job` function runs in a new process for each job that Vesper
executes. The new process is called the *main job process* for the job.
The `run_job` function is in its own module rather than in the `job_manager
module in order to minimize the number of imports that the module containing
the function, and hence the new process, must perform.
"""


from datetime import date
import json
import logging
import traceback

from vesper.command.command import CommandSyntaxError
from vesper.command.job_info import JobInfo
from vesper.command.job_logging_manager import JobLoggingManager
import vesper.util.django_utils as django_utils
import vesper.util.time_utils as time_utils


'''
Job status values:

Unstarted
Running
Completed
Interrupted
Failed
'''


class _CommandArgsEncoder(json.JSONEncoder):
    
    def default(self, obj):
        
        if isinstance(obj, date):
            return str(obj)
        
        else:
            return super().default(obj)
        
        
def run_job(job_info):
    
    """
    Runs a job in a new process.
    
    This function is executed by the Vesper job manager each time it
    starts a new job. The function is executed in a new process, called
    the *main job process* of the job.
    
    The function sets up Django and configures the root logger for the
    main job process, constructs the command to be executed, and invokes
    the command's `execute` method. Logging is shut down after that method
    returns.
    
    Parameters:
    
        job_info : `Bunch`
            information pertaining to the new job.
            
            The information includes the command specification for the
            new job, the ID of the Django Job model instance for the job,
            and the stop event for the job.
            
            The information includes the ID of the Django job model
            instance rather than the instance itself so that the job
            info can be unpickled in the new process without first
            setting up Django.
            
            This object is *not* of type `vesper.command.job_info.JobInfo`,
            which contains somewhat different (though overlapping)
            information. This function invokes the `execute` method of the
            command of the new job with an argument of type
            `vesper.command.job_info.JobInfo`.
    """
    
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
    from vesper.django.app.models import Job
    import vesper.util.archive_lock as archive_lock
    
    # Set the archive lock for this process. The lock is provided to
    # this process by its creator.
    archive_lock.set_lock(job_info.archive_lock)

    # Get the Django model instance for this job.
    job = Job.objects.get(id=job_info.job_id)
    
    # Start up logging.
    # level = logging.DEBUG if django_settings.DEBUG else logging.INFO
    level = logging.INFO
    logging_manager = JobLoggingManager(job, level)
    logging_manager.start_up_logging()
    
    # Configure root logger for the main job process.
    logger = logging.getLogger()
    logging_config = logging_manager.logging_config
    JobLoggingManager.configure_logger(logger, logging_config)
    
    try:
        
        # Mark job as running.
        job.start_time = time_utils.get_utc_now()
        job.status = 'Running'
        with archive_lock.atomic():
            job.save()
        
        # Create command from command spec.
        command = _create_command(job_info.command_spec)
        
        prefix = 'Job started for command "{}"'.format(command.name)
        
        if len(command.arguments) == 0:
            logger.info('{} with no arguments.'.format(prefix))
                        
        else:
            
            logger.info('{} with arguments:'.format(prefix))
            
            # Log command arguments JSON.
            args = json.dumps(
                command.arguments, sort_keys=False, indent=4,
                cls=_CommandArgsEncoder)
            lines = args.splitlines()
            for line in lines:
                logger.info('    {}'.format(line))
    
        # Execute command.
        info = JobInfo(job_info.job_id, logging_config, job_info.stop_event)
        complete = command.execute(info)
        
    except Exception:
        
        # Update job status and log error message
        
        job.end_time = time_utils.get_utc_now()
        job.status = 'Failed'
        with archive_lock.atomic():
            job.save()
        
        logger.error(
            'Job failed with an exception. See traceback below.\n' +
            traceback.format_exc())
        
    else:
        
        # Update job status and log final message.
        
        status = 'Completed' if complete else 'Interrupted'

        job.end_time = time_utils.get_utc_now()
        job.status = status
        with archive_lock.atomic():
            job.save()
        
        logger.info('Job {}.'.format(status.lower()))
        
    finally:
        
        # At one point this `finally` clause attempted to log a final
        # message that included counts of the critical, error, and
        # warning log messages that had been logged for this job.
        # This didn't work, however, due to a race condition. In
        # particular, there seemed to be no way for this thread to
        # ensure that all log records other than the one that it was
        # preparing had been processed by the logging thread before
        # this thread read the record counts. If all of the log
        # records had not been processed, the counts were inaccurate.
        #
        # In the future we may add record count fields to the Django
        # `Job` class so that accurate log record counts can be
        # reported in log displays. See record counts handler
        # TODO in `job_logging_manager` module for more detail.
        
        logging_manager.shut_down_logging()


def _create_count_phrase(counts, key, name):
    count = counts.get(key, 0)
    if count == 0:
        return None
    else:
        suffix = '' if count == 1 else 's'
        return '{} {} message{}'.format(count, name, suffix)


def _create_command(command_spec):

    try:
        command_name = command_spec['name']
    except KeyError:
        raise CommandSyntaxError(
            'Command specification contains no "name" item.')
        
    # This import is here rather than at the top of this module so it
    # will be executed after Django is set up in the main job process.
    #
    # The import has to be here for now only because the
    # `vesper.birdvox.detectors` module creates BirdVoxDetect detector
    # classes dynamically based on the contents of the `vesper_processor`
    # archive database table. It may not be need to be here after upcoming
    # plugin infrastructure revisions.
    from vesper.singleton.extension_manager import extension_manager
    
    command_classes = extension_manager.get_extensions('Command')
    
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
