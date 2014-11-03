"""
Shared functions pertaining to clip archives.

This module contains functions that are shared by the `Archive` class
and related classes, for example the `Station` and `Detector` classes.
It is intended that any of the modules containing those classes should
be free to import functions from the current module. These functions
would perhaps most naturally be included in the `archive` module, but
that could cause import cycles. For example, if the `station` module
had to import the `archive` module in order to use one of the
functions of the current module, then since the `archive` module
already imports the `station` module an import cycle would result.
Placing the functions in this separate module and not importing any
of the archive modules from this one avoids such cycles.

Another option would be to put the functions of this module in the
`archive` module and import that module into the `station` and other
modules not at top level, but only within the functions that need
it. This would also avoid import cycles, but have the disadvantage
of doing some import work every time one of these functions is
called, instead of only once when the module containing the function
is loaded.
"""


import datetime


def get_night(time):
    
    """
    Gets the night that includes the specified time.
    
    :Parameters:
        time : `datetime`
            the specified time.
            
    :Returns:
        the night that includes the specified time, a `date`.
        
        The night of a time is the starting date of the 24-hour period
        starting at noon that contains the time.
    """
        
    if time.hour < 12:
        time -= datetime.timedelta(hours=12)
        
    return time.date()
