"""
Singleton that manages Vesper jobs.

A Vesper job executes one Vesper command. Each job runs in its own thread,
which may or may not start additional threads. The `start_job` function of
this module starts a job for a specified command, and the `stop_job` function
requests that a running job stop.
"""


from threading import RLock

from vesper.django.app.job_thread import JobThread
from vesper.util.repeating_timer import RepeatingTimer
from vesper.vcl.command import CommandSyntaxError
import vesper.util.extension_manager as extension_manager


_command_classes = extension_manager.get_extensions('Vesper Command')
"""Mapping from Vesper command names to command classes."""

_job_threads = {}
"""
Mapping from job IDs to job threads.

A job thread is added to this dictionary when the job thread is started.
It is removed from the dictionary when it is no longer running. The
deletion is performed by the `_delete_terminated_job_threads` function,
which runs off a repeating timer.
"""

_lock = RLock()
"""
Lock used to synchronize access to the `_job_threads` dictionary from
multiple threads.
"""


def start_job(command_spec):
    thread = _create_job_thread(command_spec)
    job_id = thread.job.id
    with _lock:
        _job_threads[job_id] = thread
    thread.start()
    return job_id
    
    
def _create_job_thread(command_spec):
    
    try:
        command_name = command_spec['name']
    except KeyError:
        raise CommandSyntaxError(
            'Command specification contains no "name" item.')
        
    try:
        command_class = _command_classes[command_name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized command "{}".'.format(command_name))
        
    command_args = command_spec.get('arguments', {})
    
    command = command_class(command_args)
    
    return JobThread(command)
    

def stop_job(job_id):
    with _lock:
        try:
            thread = _job_threads[job_id]
        except KeyError:
            return
        else:
            thread.stop()
        
    
def _delete_terminated_job_threads():
    
    terminated_threads = set()
    
    with _lock:
        
        for thread in _job_threads.values():
            if not thread.is_alive():
                terminated_threads.add(thread)
                
        for thread in terminated_threads:
            job_id = thread.job.id
            print('JobManager: removing thread for job {}'.format(job_id))
            del _job_threads[job_id]


# Start repeating timer that deletes terminated job threads from `_job_threads`.
_timer = RepeatingTimer(10, _delete_terminated_job_threads)
_timer.start()
