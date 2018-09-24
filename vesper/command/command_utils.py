import logging

from vesper.command.command import CommandSyntaxError


# TODO: Add type checking to functions that get arguments.


def get_required_arg(name, args):
    try:
        return args[name]
    except KeyError:
        raise CommandSyntaxError(
            'Missing required command argument "{}".'.format(name))


def get_optional_arg(name, args, default=None):
    return args.get(name, default)


def get_timing_text(elapsed_time, item_count, items_name):
    
    # Round elapsed time to nearest tenth of a second since it
    # will be displayed at that resolution. This will keep the
    # reported item count, elapsed time, and rate consistent.
    elapsed_time = round(10 * elapsed_time) / 10
    
    time_text = ' in {:.1f} seconds'.format(elapsed_time)
    
    if elapsed_time > 0:
        
        rate = item_count / elapsed_time
        return '{}, an average of {:.1f} {} per second'.format(
            time_text, rate, items_name)
        
    else:
        # elapsed time is zero
        
        return time_text


_logger = logging.getLogger()


def log_and_reraise_fatal_exception(exception, action_text, result_text=None):
    
    error = _logger.error
    
    error('{} failed with an exception.'.format(action_text))
    error('The exception message was:')
    error('    {}'.format(str(exception)))
    
    if result_text is not None:
        error(result_text)
        
    raise
