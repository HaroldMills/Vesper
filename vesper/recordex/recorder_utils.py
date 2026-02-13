def join_with_timeout(object, timeout, logger, name):

    """
    Join a process or thread with a timeout.
    
    Log an info message if the join succeeds, or a warning if it fails.
    """

    object.join(timeout=timeout)

    if object.is_alive():
        
        logger.warning(
            f'{name} has not stopped after {timeout} seconds. '
            f'Moving on anyway.')
    
    else:
        logger.info(f'{name} has stopped.')


def close_mp_queue(queue):

    """
    Close a multiprocessing queue and wait for its feeder thread to exit.

    Every process that writes to a multiprocessing queue should call this
    function during shutdown to ensure that the queue's feeder thread exits.
    The feeder thread is non-daemonic, so if it does not exit it will prevent
    the process from exiting.
    """

    queue.close()
    queue.join_thread()
