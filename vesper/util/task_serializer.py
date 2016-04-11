"""Module containing `TaskSerializer` class."""


from queue import Queue
from threading import Thread


class TaskSerializer(object):
    
    """
    Task serializer that runs submitted tasks on a single thread.
    
    Tasks may be submitted on any number of threads, but all are run
    on a single thread, called the *task thread*. Tasks are run in
    FIFO order, and each task is run synchronously: the submitting
    thread waits until the task completes.
    """
    
    
    def __init__(self):
        super(TaskSerializer, self).__init__()
        self._queue = Queue(maxsize=1)
        self._thread = _Thread(self._queue)
        self._thread.start()
        
        
    def execute(self, callable_, *args, **kwds):
        
        """
        Executes a task synchronously on the task thread.
        
        This method invokes the specified callable on the specified
        arguments.
        
        :Returns:
            the value returned by the callable.
            
        :Raises TaskError:
            if the callable raised an exception.
            
            The exception raised by the callable is the `exception` member
            of the exception raised by this method.
        """
        
        task = _Task(callable_, *args, **kwds)
        
        self._queue.put(task)
        
        # Wait for task to complete
        self._queue.join()
        
        if task.exception is not None:
            # TODO: Is there some way to preserve the stack trace of the
            # original exception when we re-raise it?
            raise task.exception
        else:
            return task.result
            
            
class _Thread(Thread):
    
    
    def __init__(self, queue):
        super(_Thread, self).__init__()
        self.daemon = True
        self._queue = queue
        
        
    def run(self):
        while True:
            task = self._queue.get()
            task.execute()
            self._queue.task_done()
        
        
class _Task(object):
    
    
    def __init__(self, callable_, *args, **kwds):
        super(_Task, self).__init__()
        self._callable = callable_
        self._args = args
        self._kwds = kwds
        
        
    def execute(self):
        self.exception = None
        try:
            self.result = self._callable(*self._args, **self._kwds)
        except Exception as e:
            self.exception = e
            
    