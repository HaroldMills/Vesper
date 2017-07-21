"""
Module containing the Vesper archive lock.

The archive lock is used to prevent concurrent writes to Vesper
archives from more than one thread and/or process. For the time
being, at least, we have resorted to using such a lock since we
have had problems with concurrent SQLite database transactions
raising Django `OperationalError` exceptions with the message
"database is locked". Proper use of the lock prevents these
errors by ensuring that only one transaction is attempted at
a time.

To use the lock, any code that writes to an archive should run
inside a Python `with` statement whose context manager is the loxk.
Note that when a transaction surrounds a sequence of writes, the
transaction should be initiated only *after* acquiring the lock.

Care must be taken to ensure that a single archive lock is shared
by all processes that may write to an archive. For example, only
one process should import this module, and the lock of that process
should then be provided to any other processes that need it. No
other process should import this module, since that would create
a second lock. [This will work for the Django development server,
which (at least as of Django 1.11) runs in a single process, but
I'm not sure it will work for, say, uWSGI deployments that handle
requests with multiple processes.]

Use of the lock slows database writes, but without it writes to an
SQLite archive database fail if more than one thread and/or process
attempts to write to the database at once. For example, we have seen
this problem when trying to classify all of the clips of a clip album
page with a single keystroke, and even when trying to classify multiple
clips with one keystroke per clip on a slow computer. Even though each
clip classification was attempted on the server in its own database
transaction, assuring atomicity, many classification requests (one for
each clip) went to the server in quick succession, resulting in multiple
concurrent transactions, some of which failed. A Django `OperationalError`
exception was raised for each failed transaction, with the message
"database is locked".

Vesper archives that use a database engine (perhaps PostgreSQL, for
example) that supports concurrent writes better than SQLite may not
require this lock. In that case, we could make the value of the
`archive_lock` attribute of this module an instance of our own
context manager that can behave differently for different database
back ends. Such a context manager might behave as the current one
does when the database back end is SQLite, but do nothing when it
is PostgreSQL.

I also tried using a semaphore that allowed just two concurrent
transactions (see commented-out code below) and setting the SQLite
database timeout to one second (by modifying the `DATABASES`
attribute in the project settings appropriately: see the
'"Database is locked" errors' section of
https://docs.djangoproject.com/en/1.11/ref/databases/#sqlite-notes),
but that also resulted in "database is locked" errors. The errors
started appearing more or less immediately after a keystroke to
classify all of the clips of a page, rather than one second after,
which suggests to me that the problem isn't just that the database
has limited support for concurrent transactions, but rather that it
does not support concurrent transactions at all, at least as
configured here.
"""


from multiprocessing import RLock
  
  
archive_lock = RLock()


# from multiprocessing import Semaphore
# 
# 
# archive_lock = Semaphore(1)


# class _NoOpContextManager:
#     
#     
#     def __enter__(self):
#         pass
#     
#     
#     def __exit__(self, *args):
#         pass
#     
#     
# archive_lock = _NoOpContextManager()
