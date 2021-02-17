"""Utility functions pertaining to text."""


from datetime import timedelta as TimeDelta
import math
import re


def create_string_item_list(items):
    
    """
    Creates a human-readable string for a list of items.
    
    Examples:
    
        [] -> ''
        ['one'] -> 'one'
        ['one', two'] -> 'one and two'
        ['one', 'two', 'three'] -> 'one, two, and three'
        ['one', 'two', 'three', 'four'] -> 'one, two, three, and four'
        [1, 2, 3] -> '1, 2, and 3'
    """
    
    items = [str(i) for i in items]
    
    n = len(items)
    
    if n == 0:
        return ''
    
    elif n == 1:
        return items[0]
    
    elif n == 2:
        return items[0] + ' and ' + items[1]
    
    else:
        final_item = 'and ' + items[-1]
        return ', '.join(items[:-1] + [final_item])


def format_number(x):
    
    """
    Formats a nonnegative number either as an integer if it rounds to
    at least ten, or as a decimal rounded to two significant digits.
    """
    
    if x == 0:
        return '0'
    
    else:
        
        i = int(round(x))
        
        if i < 10:
            
            # Get `d` as decimal rounded to two significant digits.
            
            xx = x
            n = 0
            while xx < 10:
                xx *= 10
                n += 1
            f = '{:.' + str(n) + 'f}'
            return f.format(x)
    
        else:
            return str(i)


_FRACTION_RE = re.compile('\.(\d{6})')


def format_datetime(dt, format_, fraction_digit_count=None):
    
    formatted_dt = dt.strftime(format_)
    
    if fraction_digit_count is not None and fraction_digit_count < 6:
        # fractional digit count specifies different number of digits
        # than provided by "%f" format code
        
        # The "%f" format code of the `strftime` function (see
        # https://docs.python.org/3/library/datetime.html#
        # strftime-and-strptime-format-codes) yields six fractional
        # second digits, i.e. microsecond precision. When
        # `fraction_digit_count` is specified and less than six, we
        # reduce that precision accordingly.
        
        # Find all occurrences of a decimal point followed by six
        # digits in the formatted time.
        matches = list(_FRACTION_RE.finditer(formatted_dt))
        
        if len(matches) != 0:
            # found decimal point followed by six digits
            
            # We assume here that if the formatted time includes any
            # occurrences of a decimal point followed by six digits,
            # the last one is the fractional part of the time. That
            # seems like it should be a fairly safe assumption in
            # practice, though in principle it is easy to construct
            # cases in which it is false. It might be desirable to
            # use a custom formatting language eventually that we
            # parse ourselves, so that we control the number of
            # formatted fractional digits from the start, but that's
            # a lot more work.
            match = matches[-1]
            
            extra_digit_count = 6 - fraction_digit_count
            extra_digit_power = 10 ** extra_digit_count
            
            # Get fraction in microseconds.
            microseconds = int(match.group(1))
            
            # Scale to units of last fractional digit to retain.
            units = microseconds / extra_digit_power
            
            rounded_units = round(units)
            floored_units = math.floor(units)
            
            if rounded_units != floored_units:
                # rounding will be up to nearest unit instead of down
                
                # Get time floored to nearest unit.
                floored_microseconds = floored_units * extra_digit_power
                dt = dt.replace(microsecond=floored_microseconds)
                
                # Add one unit.
                unit = 10 ** -fraction_digit_count
                dt = dt + TimeDelta(seconds=unit)
                
                # Reformat altered time.
                formatted_dt = dt.strftime(format_)
            
            # Get formatted time minus extra trailing fractional digits.
            if fraction_digit_count == 0:
                point_offset = 0
            else:
                point_offset = 1
            start_index = match.start() + fraction_digit_count + point_offset
            end_index = start_index + extra_digit_count + 1 - point_offset
            formatted_dt = \
                formatted_dt[:start_index] + formatted_dt[end_index:]
    
    return formatted_dt


def format_time_difference(
        seconds, hours_digit_count=None, fraction_digit_count=0):
    
    # Get format for hours and minutes part of time difference.
    if hours_digit_count is None:
        hours_format = '{:d}'
    else:
        hours_format = '{:0' + str(hours_digit_count) + '}'
    hours_minutes_format = hours_format + ':{:02d}'
    
    # Get format for seconds part of time difference, including
    # fraction (if present).
    seconds_format = f'{{:.{fraction_digit_count}f}}'
    
    # Get sign prefix.
    if seconds < 0:
        seconds = -seconds
        prefix = '-'
    else:
        prefix = ''
    
    # Format hours and minutes.
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    hours_minutes = hours_minutes_format.format(hours, minutes)
    
    # Format integer and fractional parts of seconds together to
    # get appropriate rounding.
    seconds = seconds_format.format(seconds)
    
    # Split integer part and fractional part (if present) to handle
    # separately below.
    parts = seconds.split('.')
    
    # Pad seconds with zero on left if needed.
    seconds = parts[0].rjust(2, '0')
    
    # Get fraction (if present).
    if len(parts) == 1:
        fraction = ''
    else:
        fraction = '.' + parts[1]
    
    return f'{prefix}{hours_minutes}:{seconds}{fraction}'


def create_count_text(count, singular_units_text, plural_units_text=None):
    units = create_units_text(count, singular_units_text, plural_units_text)
    return '{} {}'.format(count, units)


def create_units_text(quantity, singular_units_text, plural_units_text=None):
    
    if quantity == 1:
        return singular_units_text
    
    elif plural_units_text is not None:
        return plural_units_text
    
    else:
        return singular_units_text + 's'
