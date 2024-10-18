"""
Multiprocessing for the Vesper Recorder.

All Vesper Recorder code should import multiprocessing classes such
as `Process`, `Queue`, and `Event` from this module instead of the
`multiprocessing` module of the Python Standard Library. Importing
from this module ensures that the *spawn* start method is used for
all processes on all platforms. This is not the case if you use the
`multiprocessing` module directly.

As of Python 3.12, the default start method is *spawn on Windows and
macOS, but it is *fork* on POSIX systems other than macOS, including
Linux. However, the documentation for the `multiprocessing` module
of Python 3.12 also inicates that the "the default start method will
change away from *fork* in Python 3.14". If with that change it
becomes *spawn* on all platforms, this module will no longer be
needed.
"""


import multiprocessing


# Get `multiprocessing` context object that uses the *spawn* start method.
# We use this context object to create processes and queues consistently
# on all platforms.
_context = multiprocessing.get_context('spawn')


# Multiprocessing classes from `_context`. Add others as needed.
Process = _context.Process
Queue = _context.Queue
Event = _context.Event
