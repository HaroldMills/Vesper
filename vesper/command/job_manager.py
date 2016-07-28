"""Module containing `JobManager` class."""


from threading import RLock
import logging

from vesper.command.command import CommandSyntaxError
from vesper.command.job_thread import JobThread
from vesper.util.repeating_timer import RepeatingTimer


class JobManager:
    
    """
    Manager of Vesper jobs.

    A Vesper job executes one Vesper command. Each job runs in its own
    thread, which may or may not start additional threads. The `start_job`
    method of this class starts a job for a specified command, and the
    `stop_job` method requests that a running job stop. A job is not
    required to honor a stop request, but most jobs should, especially
    longer-running ones.
    """
    
    
    def __init__(self, command_classes):
        
        self._command_classes = command_classes.copy()
        """Mapping from Vesper command names to command classes."""

        self._job_threads = {}
        """
        Mapping from job IDs to job threads.
        
        A job thread is added to this dictionary when the job thread is
        started. It is removed from the dictionary when it is no longer
        running. The removal is performed by the
        `_delete_terminated_job_threads` method, which runs off a
        repeating timer.
        """

        self._lock = RLock()
        """
        Lock used to synchronize access to the `_job_threads` dictionary
        from multiple threads.
        """

        self._timer = RepeatingTimer(10, self._delete_terminated_job_threads)
        """
        Repeating timer that deletes terminated job threads from
        `_job_threads`.
        """
        
        self._timer.start()


    def start_job(self, command_spec):
        thread = self._create_job_thread(command_spec)
        job_id = thread.job.id
        with self._lock:
            self._job_threads[job_id] = thread
        thread.start()
        return job_id
        
        
    def _create_job_thread(self, command_spec):
        
        try:
            command_name = command_spec['name']
        except KeyError:
            raise CommandSyntaxError(
                'Command specification contains no "name" item.')
            
        try:
            command_class = self._command_classes[command_name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized command "{}".'.format(command_name))
            
        command_args = command_spec.get('arguments', {})
        
        command = command_class(command_args)
        
        return JobThread(command)
        
    
    def stop_job(self, job_id):
        with self._lock:
            try:
                thread = self._job_threads[job_id]
            except KeyError:
                return
            else:
                thread.stop()
            
        
    def _delete_terminated_job_threads(self):
        
        terminated_threads = set()
        
        with self._lock:
            
            for thread in self._job_threads.values():
                if not thread.is_alive():
                    terminated_threads.add(thread)
                    
            for thread in terminated_threads:
                job_id = thread.job.id
                logging.info(
                    'JobManager: removing thread for job {}'.format(job_id))
                del self._job_threads[job_id]
