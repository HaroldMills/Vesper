"""Module containing class `JobManager`."""


from multiprocessing import Event, Lock, Process
import datetime
import json

from vesper.django.app.models import Job
from vesper.util.bunch import Bunch
from vesper.util.repeating_timer import RepeatingTimer
import vesper.command.job_runner as job_runner
import vesper.util.archive_lock as archive_lock
import vesper.util.time_utils as time_utils


class JobManager:
    
    """
    Manager of Vesper jobs.

    A Vesper job executes one Vesper command. Each job runs in its own
    process, which may or may not start additional processes. The
    `start_job` method of this class starts a job for a specified command,
    and the `stop_job` method requests that a running job stop. A job is
    not required to honor a stop request, but most jobs should, especially
    longer-running ones.
    """
    
    
    def __init__(self):
        
        self._job_infos = {}
        """
        Mapping from job IDs to `Bunch` objects containing job information.
        
        An item is added to this dictionary when each job is started.
        A job's item is removed from the dictionary after the job terminates.
        The removal is performed by the `_delete_terminated_jobs` method,
        which runs off a repeating timer.
        """

        self._lock = Lock()
        """
        Lock used to synchronize access to the `_job_infos` dictionary
        from multiple threads. (The lock can synchronize access from
        multiple threads and/or processes, but we access the dictionary
        only from threads of the main Vesper process.)
        """

        self._timer = RepeatingTimer(10, self._delete_terminated_jobs)
        """Repeating timer that deletes terminated jobs from `_job_infos`."""
        
        self._timer.start()


    def start_job(self, command_spec, user):
        
        info = Bunch()
        info.command_spec = command_spec
        info.job_id = _create_job(command_spec, user)
        info.archive_lock = archive_lock.get_lock()
        info.stop_event = Event()

        with self._lock:
            self._job_infos[info.job_id] = info
            
        info.process = Process(target=job_runner.run_job, args=(info,))
        info.process.start()
        
        return info.job_id
        
        
    def stop_job(self, job_id):
        with self._lock:
            try:
                job_info = self._job_infos[job_id]
            except KeyError:
                return
            else:
                job_info.stop_event.set()
            
        
    def _delete_terminated_jobs(self):
        
        terminated_job_ids = set()
        
        with self._lock:
            
            for info in self._job_infos.values():
                if not info.process.is_alive():
                    terminated_job_ids.add(info.job_id)
                    
            for job_id in terminated_job_ids:
                del self._job_infos[job_id]


def _create_job(command_spec, user):
    
    with archive_lock.atomic():
        job = Job.objects.create(
            command=json.dumps(command_spec, default=_json_date_serializer),
            creation_time=time_utils.get_utc_now(),
            creating_user=user,
            status='Unstarted')
    
    return job.id
    
    
def _json_date_serializer(obj):
    
    """Date serializer for `json.dumps`."""
    
    if isinstance(obj, datetime.date):
        return str(obj)
    else:
        raise TypeError('{} is not JSON serializable'.format(repr(obj)))
