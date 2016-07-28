"""Module containing class `JobThread`."""


from threading import Event, Thread
import datetime
import json
import pprint
import traceback

from vesper.django.app.models import Job, User
import vesper.util.time_utils as time_utils


'''
Job status values:

Not Started
Running
Complete
Interrupted
Raised Exception
'''


class JobThread(Thread):
    
    
    @staticmethod
    def _create_job(command):
        
        command_spec = {
            'name': command.name,
            'arguments': command.arguments
        }
        
        # TODO: This should be the logged-in user.
        user = User.objects.get(username='Harold')
        
        job = Job(
            command=json.dumps(command_spec, default=_json_date_serializer),
            creation_time = time_utils.get_utc_now(),
            creating_user=user,
            status='Not Started')
        job.save()
        
        return job
    
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.job = JobThread._create_job(self.command)
        self._stop_event = Event()
        
        
    def start(self):
        
        job = self.job
        
        # Set job start time and status in database. We do this before starting
        # the job thread to avoid a race condition that could result in the
        # job end information being written before the job start information.
        job.start_time = time_utils.get_utc_now()
        job.status = 'Running'
        job.save()
        
        command_args = pprint.pformat(self.command.arguments, indent=1)
        command_args = _indent_lines(command_args, 4)
        job.logger.info(
            'Job started for command "{}" with arguments:\n{}'.format(
                self.command.name, command_args))
        
        super().start()
        
        
    def run(self):
        
        job = self.job
        
        context = _CommandContext(self)
        
        try:
            complete = self.command.execute(context)
            
        except Exception:
            job.end_time = time_utils.get_utc_now()
            job.status = 'Raised Exception'
            job.save()
            job.logger.error('Job raised exception.\n' + traceback.format_exc())
            
        else:
            
            job.end_time = time_utils.get_utc_now()
            
            if complete:
                job.status = 'Complete'
                log_message = 'Job complete.'
                
            else:
                job.status = 'Interrupted'
                log_message = 'Job interrupted.'
                
            job.save()
            job.logger.info(log_message)
        
        
    def stop(self):
        self._stop_event.set()
        
        
    def _stop_requested(self):
        return self._stop_event.is_set()


def _indent_lines(text, num_spaces):
    prefix = ' ' * num_spaces
    lines = text.split('\n')
    indented_lines = [prefix + line for line in lines]
    return '\n'.join(indented_lines)


class _CommandContext(object):
    
    def __init__(self, job_thread):
        self._job_thread = job_thread
        
    @property
    def stop_requested(self):
        return self._job_thread._stop_requested()
    
    @property
    def job(self):
        return self._job_thread.job
    

def _json_date_serializer(obj):
    
    """Date serializer for `json.dumps`."""
    
    if isinstance(obj, datetime.date):
        return str(obj)
    else:
        raise TypeError('{} is not JSON serializable'.format(repr(obj)))
    