"""Module containing class `RepeatingTimer`."""


from threading import Thread, Timer


class RepeatingTimer(Thread):
    
    """Timer that fires repeatedly."""
    
    
    def __init__(self, interval, function, args=None, kwargs=None):
        super().__init__()
        self._interval = interval
        self._function = function
        self._args = args if args is not None else {}
        self._kwargs = kwargs if kwargs is not None else {}
        self._timer = None
        self._started = False
        
        
    def start(self):
        if self._started:
            raise ValueError('RepeatingTimer can be started only once.')
        else:
            self._start_timer()
        
        
    def _start_timer(self):
        self._timer = Timer(self._interval, self._tick)
        self._timer.start()
        
        
    def _tick(self):
        self._function(*self._args, **self._kwargs)
        self._start_timer()
        
        
    def cancel(self):
        if self._timer is not None:
            self._timer.cancel()
