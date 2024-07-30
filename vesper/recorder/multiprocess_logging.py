"""Utility functions for multiprocess logging."""


from logging.handlers import QueueHandler


logging_queue = None
"""
`multiprocess.Queue` created and read by the main Vesper Recorder process
and written to by other processes.
"""


def create_logging_handler():

    """
    Creates a logging handler for this process.

    The logging handler is a `QueueHandler` that forwards messages
    written to it to the logging process.
    """

    # TODO: Check that `logging_queue` is not `None`?
    return QueueHandler(logging_queue)
