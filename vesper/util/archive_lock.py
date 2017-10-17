"""
Module containing the Vesper archive lock.

The archive lock is used by Vesper threads and/or processes to prevent
concurrent archive database transactions. For the time being, at least,
we have resorted to using such a lock since we have had problems with
concurrent SQLite database transactions failing due to timeouts. Such
a timeout occurs if an SQLite transaction begins but then can't obtain
the (internal) SQLite database lock before a timeout period expires.
This can happen if another transaction is in progress in another thread
or process that runs for longer than the timeout period. A timeout
manifests as a Django `OperationalError` exception with the message
"database is locked". Proper use of the archive lock prevents such
errors by ensuring that only one transaction is attempted at a time.

As a specific example, before introducing the archive lock we saw
"database is locked" errors when trying to classify all of the clips
of a clip album page with a single keystroke (such a keystroke used
to initiate multiple annotation requests to the server: now it
initiates only one), and even when trying to classify multiple clips
with one keystroke per clip on a slow computer. Even though each clip
classification was attempted on the server in its own database
transaction, ensuring atomicity, many classification requests
(one for each clip) went to the server in quick succession, resulting
in multiple concurrent transactions, some of which timed out.

To use the archive lock, any query that writes to the archive database
should be executed only after obtaining the lock, either via a
`with archive_lock.atomic():` statement or via an `@archive_lock.atomic`
decorator. Note that the lock should be obtained even if the query is
not explicitly part of a transaction, since by default each Django
query is wrapped in its own transaction if a transaction is not already
active: see the "Autocommit" section of
https://docs.djangoproject.com/en/1.11/topics/db/transactions/.
When a transaction surrounds a sequence of writes, the transaction
should be initiated only *after* acquiring the lock.

Care must be taken to ensure that a single archive lock is shared by
all processes that may write to an archive. For example, only one
process should call this module's `create_lock` function, and the
resulting lock should then be passed to other processes for them to
use.

Vesper archives that use a database engine that supports concurrent
writes better than SQLite (perhaps PostgreSQL, for example) may not
require this lock. In that case, we could make the value of the
`_lock` attribute of this module an instance of our own context
manager that can behave differently for different database back ends.
Such a context manager might behave as the current one does when the
database back end is SQLite, but do nothing when the back end is
PostgreSQL.

I also tried using a semaphore that allowed just two concurrent
transactions (see commented-out code below) and setting the SQLite
database timeout to one second (by modifying the `DATABASES`
attribute in the project settings appropriately: see the
'"Database is locked" errors' section of
https://docs.djangoproject.com/en/1.11/ref/databases/#sqlite-notes),
but that also resulted in "database is locked" errors. The errors
started appearing more or less immediately after a keystroke to
classify all of the clips of a page, rather than one second after,
which suggests to me that the problem may not be just that the
database has limited support for concurrent transactions, but
rather that for some reason it does not support concurrent
transactions at all.
"""


from multiprocessing import RLock

from vesper.archive_settings import archive_settings


class DoNothingLock:
     
    """Do-nothing replacement for RLock."""
    
    def __enter__(self):
        pass
  
    def __exit__(self, *args):
        pass


_lock = None


def create_lock():
    
    if archive_settings.database.engine == 'SQLite':
        lock_class = RLock
    else:
        lock_class = DoNothingLock
        
    set_lock(lock_class())


def set_lock(lock):
    global _lock
    _lock = lock
     
     
def get_lock():
    _check_lock()
    return _lock
 
 
def _check_lock():
    if _lock is None:
        raise ValueError('Archive lock has not yet been created or set.')
 
 
def atomic(arg=None):
    
    """
    This function can be used in two modes: context manager mode and
    decorator mode. In context manager mode, it is invoked without an
    argument and returns the archive lock. In decorator mode, it is
    invoked on a callable and returns a function that invokes the
    callable after obtaining the archive lock.
    """
    
    _check_lock()
    
    if arg is None:
        # invoked without argument
        
        # Context manager mode: return archive lock.
        return _lock
    
    elif callable(arg):
        # invoked on callable
        
        # Decorator mode: return function that invokes argument after
        # obtaining archive lock.
        
        def decorated(*args, **kwargs):
            with _lock:
                arg(*args, **kwargs)
                
        return decorated
    
    else:
        # invoked on something other than a callable
        
        raise ValueError(
            'Decorator argument does not appear to be a callable.')
