"""Utility functions pertaining to text."""


from datetime import timedelta as TimeDelta
import itertools
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


_FRACTION_CODE_RE = re.compile('%([1-6])f')
_FRACTION_PLACEHOLDER = '<~!@#$^&*>'


def format_datetime(dt, format_):
    
    # Adjust format for use by `datetime.strftime`, replacing
    # modified fraction codes with placeholders and retaining digit
    # counts separately.
    format_, digit_counts = _adjust_datetime_format(format_)
    
    # Format with `datetime.strftime`.
    formatted_datetime = dt.strftime(format_)
    
    # Replace sentinels with fractional seconds.
    return _add_fractional_seconds(formatted_datetime, digit_counts, dt)


def _adjust_datetime_format(format_):
    
    # Split format at double percents. This yields the segments of
    # the format we need to search for modified fraction codes. It's
    # important to get rid of the double percents at the start so
    # they don't interfere with the search for modified fraction codes.
    # Consider the format "%%3f", for example, which does not
    # indicate a fractional second but rather the string "%3f".
    format_segments = format_.split('%%')
    
    # Replace modified fraction codes with placeholders, retaining
    # digit counts separately.
    pairs = [_adjust_datetime_format_aux(s) for s in format_segments]
    
    # Zip pairs into format segments and digit counts.
    format_segments, digit_count_lists = zip(*pairs)
    
    # Join format segments with double percents.
    format_ = '%%'.join(format_segments)
    
    # Flatten digit count lists.
    digit_counts = list(itertools.chain.from_iterable(digit_count_lists))
    
    return format_, digit_counts


def _adjust_datetime_format_aux(format_segment):
    
    # Split format segment at modified fraction codes.
    parts = _FRACTION_CODE_RE.split(format_segment)
    
    # Deinterleave format subsegments and digit counts.
    format_subsegments = parts[::2]
    digit_counts = [int(d) for d in parts[1::2]]
    
    # Rejoin format subsegments with fraction placeholder.
    format_segment = _FRACTION_PLACEHOLDER.join(format_subsegments)
    
    return format_segment, digit_counts


def _add_fractional_seconds(formatted_datetime, digit_counts, dt):
    
    # Split formatted `datetime` at fraction placeholder.
    other_segments = formatted_datetime.split(_FRACTION_PLACEHOLDER)
    
    # Create fraction segments to substitute for placeholders.
    microsecond = f'{dt.microsecond:06d}'
    fraction_segments = [microsecond[:c] for c in digit_counts]
    
    # Append empty string to fraction segments to have same number
    # of those as other segments.
    fraction_segments.append('')
    
    # Interleave two types of segments and join.
    pairs = zip(other_segments, fraction_segments)
    segments = itertools.chain.from_iterable(pairs)
    return ''.join(segments)


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
