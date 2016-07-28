"""Module containing class `CalendarMonth`."""


import functools


@functools.total_ordering
class CalendarMonth:
    
    """
    A calendar month, with a year and a month.
    
    A `CalendarMonth` object has integer `year` and `month` attributes.
    
    `CalendarMonth` objects are immutable, hashable, and totally ordered.
    
    You can add and subtract integer numbers of months to and from a
    `CalendarMonth`. Subtracting one `CalendarMonth` from another yields
    an integer number of months.
    
    The `range` method iterates over sequences of `CalendarMonth` values.
    """
    
    
    @staticmethod
    def from_date(date):
        return CalendarMonth(date.year, date.month)


    @staticmethod
    def range(from_month, to_month):
        
        if not isinstance(from_month, CalendarMonth) or \
                not isinstance(to_month, CalendarMonth):
            raise TypeError('Both arguments must be `CalendarMonth` objects.')
        
        if to_month > from_month:
            month = from_month
            while month != to_month:
                yield month
                month += 1
        
        
    def __init__(self, year, month):
        
        if not isinstance(year, int) or not isinstance(month, int):
            raise TypeError('Year and month must both be integers.')
            
        if month < 1 or month > 12:
            raise ValueError(
                'Specified month {} is not between 1 and 12.'.format(month))
            
        self._n = year * 12 + (month - 1)
        
        
    @property
    def year(self):
        return _year(self._n)
    
    
    @property
    def month(self):
        return _month(self._n)
    
    
    def __repr__(self):
        return 'CalendarMonth({}, {})'.format(self.year, self.month)
    
    
    def __str__(self):
        return '{:4d}-{:02d}'.format(self.year, self.month)
    
    
    def __hash__(self):
        return self._n
    
    
    def __eq__(self, other):
        if not isinstance(other, CalendarMonth):
            return False
        else:
            return other._n == self._n
        
        
    def __lt__(self, other):
        if not isinstance(other, CalendarMonth):
            return False
        else:
            return self._n < other._n
        
        
    def __add__(self, i):
        if not isinstance(i, int):
            return NotImplemented
        else:
            n = self._n + i
            return CalendarMonth(_year(n), _month(n))
        
        
    def __radd__(self, i):
        return self.__add__(i)
    
    
    def __sub__(self, other):
        if isinstance(other, CalendarMonth):
            return self._n - other._n
        elif isinstance(other, int):
            n = self._n - other
            return CalendarMonth(_year(n), _month(n))
        else:
            raise NotImplemented
        
        
def _year(n):
    return n // 12


def _month(n):
    return (n % 12) + 1
