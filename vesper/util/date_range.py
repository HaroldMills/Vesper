"""Module containing class `DateRange`."""


import datetime


_ONE_DAY = datetime.timedelta(days=1)


class DateRange:
    
    """
    Iterator for a range of dates.
    
    This class currently supports only increasing sequences of dates
    with a step size of one day.
    """
    
    
    def __init__(self, start, stop):
        self._start = start
        self._stop = stop
    
    
    @property
    def start(self):
        return self._start
    
    
    @property
    def stop(self):
        return self._stop
    
    
    def __iter__(self):
        self._date = self._start
        return self
    
    
    def __next__(self):
        if self._date >= self._stop:
            raise StopIteration
        else:
            result = self._date
            self._date += _ONE_DAY
            return result
