"""Module containing class `JobThread`."""


from threading import Event, Thread
import json
import traceback

from vesper.django.app.models import Job, User
import vesper.util.time_utils as time_utils


'''
Job status values:

not started
running
complete
stopped by request
raised exception
'''


class JobThread(Thread):
    
    
    @staticmethod
    def _create_job(command):
        
        # TODO: This should be the logged-in user.
        user = User.objects.get(username='Harold')
        
        job = Job(
            command=json.dumps(command.spec),
            creation_time = time_utils.get_utc_now(),
            creating_user=user,
            status='not started')
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
        job.status = 'running'
        job.save()
        
        job.logger.info('Job started. Command is: {}'.format(job.command))
        
        super().start()
        
        
    def run(self):
        
        job = self.job
        
        try:
            context = _CommandContext(self)
            complete = self.command.execute(context)
            
        except Exception:
            job.end_time = time_utils.get_utc_now()
            job.status = 'raised exception'
            job.save()
            job.logger.error('Job raised exception.\n' + traceback.format_exc())
            
        else:
            
            job.end_time = time_utils.get_utc_now()
            
            if complete:
                job.status = 'complete'
                log_message = 'Job complete.'
                
            else:
                job.status = 'stopped by request'
                log_message = 'Job stopped by request before completion.'
                
            job.save()
            job.logger.info(log_message)
        
        
    def stop(self):
        self._stop_event.set()
        
        
    def _stop_requested(self):
        return self._stop_event.is_set()


class _CommandContext(object):
    
    def __init__(self, job_thread):
        self._job_thread = job_thread
        
    @property
    def stop_requested(self):
        return self._job_thread._stop_requested()
    
    @property
    def job(self):
        return self._job_thread.job
    