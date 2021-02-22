"""Utility functions pertaining to text."""


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


class _DifferenceFormatter:
    
    
    _METHOD_NAMES = {
        '%': '_format_percent'
    }
    
    
    def format(self, difference, format_code):
        
        char = format_code[-1]
        method_name = self._METHOD_NAMES.get(char, f'_format_{char}')
        method = getattr(self, method_name)
        
        # This yields the empty list for format codes that have no
        # arguments, or a length-one list containing a digit for an
        # "f" format code with an argument.
        args = list(format_code)[:-1]
        
        return method(difference, *args)
    
    
    def _format_G(self, d):
        if d > 0:
            return '+'
        elif d < 0:
            return '-'
        else:
            return ''
    
    
    def _format_g(self, d):
        if d < 0:
            return '-'
        else:
            return ''
    
    
    def _format_d(self, d):
        days = math.floor(abs(d) // (24 * 3600))
        return str(days)
    
    
    def _format_H(self, d):
        hours = math.floor((abs(d) // 3600) % 24)
        return f'{hours:02d}'
    
    
    def _format_h(self, d):
        hours = math.floor(abs(d) // 3600)
        return str(hours)
    
    
    def _format_M(self, d):
        minutes = math.floor((abs(d) // 60) % 60)
        return f'{minutes:02d}'
    
    
    def _format_m(self, d):
        minutes = math.floor(abs(d) // 60)
        return str(minutes)
    
    
    def _format_S(self, d):
        seconds = math.floor(abs(d)) % 60
        return f'{seconds:02d}'
    
    
    def _format_s(self, d):
        seconds = math.floor(abs(d))
        return str(seconds)
    
    
    def _format_f(self, d, digit_count='6'):
        
        # Get microseconds as string of six digits.
        d = abs(d)
        fraction = d - math.floor(d)
        microseconds = int(fraction * 1e6)
        digits = str(microseconds)
        
        # Truncate to specified number of digits.
        digit_count = int(digit_count)
        return digits[:digit_count]
    
    
    def _format_percent(self, d):
        return '%'


#     %G - sign, "-" if negative, "+" if not
#     %g - sign, "-" if negative, "" if not
#     %d - number of whole days
#     %H - two-digit number of whole hours modulo 24
#     %h - number of whole hours
#     %M - two-digit number of whole minutes modulo 60
#     %m - number of whole minutes
#     %S - two-digit number of whole seconds modulo 60
#     %s - number of whole seconds
#     %f - six-digit fractional second
#     %<n>f - n-digit fractional second, with 1 <= n <= 6
#     %% - percent


_DIFFERENCE_FORMATTER = _DifferenceFormatter()

_FORMAT_CODE_RE = re.compile('%([GgdHhMmSsf%]|[1-6]f)')


def format_time_difference(difference, format_):
    
    parts = _FORMAT_CODE_RE.split(format_)
    
    literal_segments = parts[::2]
    format_codes = parts[1::2]
    
    formatted_segments = [
        _DIFFERENCE_FORMATTER.format(difference, c) for c in format_codes]
    
    formatted_segments.append('')
    
    segment_pairs = zip(literal_segments, formatted_segments)
    segments = itertools.chain.from_iterable(segment_pairs)
    return ''.join(segments)


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
