def join_with_timeout(object, timeout, logger, name):

    """
    Join a process or thread with a timeout.
    
    Log an info message if the join succeeds, or a warning if it fails.

    Return `True` if and only if the join succeeds.
    """

    object.join(timeout=timeout)

    if object.is_alive():

        logger.warning(
            f'{name} has not stopped after {timeout} seconds. '
            f'Moving on anyway.')
        
        return False
    
    else:
        logger.info(f'{name} has stopped.')
        return True
