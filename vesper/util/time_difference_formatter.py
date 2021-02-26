"""Module containing class `TimeDifferenceFormatter`."""


import itertools
import math
import re


_FORMAT_CODE_RE = re.compile('%([GgdHhMmSsf%]|[1-6]f)')
"""Regular expression for all format codes."""

_FORMAT_CODE_TIME_INCREMENTS = {
    'G': None,
    'g': None,
    'd': 24 * 3600,
    'H': 3600,
    'h': 3600,
    'M': 60,
    'm': 60,
    'S': 1,
    's': 1,
    'f': .000001,
    '1f': .1,
    '2f': .01,
    '3f': .001,
    '4f': .0001,
    '5f': .00001,
    '6f': .000001,
    '%': None
}
"""
Mapping from format codes to minimum formatted time increments in seconds .
"""

_FORMATTING_METHOD_NAMES = {
    '%': '_format_percent'
}
"""Mapping from format characters to corresponding formatter method names."""


class TimeDifferenceFormatter:
    
    """Formats time differences according to a format string."""
    
    
    @staticmethod
    def get_min_time_increment(format_string):
        
        """
        Gets the minimum nonzero increment between two time
        differences as formatted with the specified format string.
        """
        
        
        # Get format codes of format string.
        _, format_codes = _parse_format_string(format_string)
        
        # Get format code time increments.
        increments = [_FORMAT_CODE_TIME_INCREMENTS[c] for c in format_codes]
        
        # Exclude `None` time increments.
        increments = [i for i in increments if i is not None]
        
        if len(increments) == 0:
            return None
        else:
            return min(increments)
    
    
    def __init__(self, format_string):
        
        """
        Initializes a time difference formatter for the specified format
        string.
        
        Parameters
        ----------
        format_string : str
            the format according to which to format time differences.
            
            In addition to literal characters, the format can contain
            the following format codes:
            
                %G - sign, "-" if difference negative, "+" if not
                %g - sign, "-" if difference negative, "" if not
                %d - number of whole days
                %H - two-digit number of whole hours modulo 24
                %h - number of whole hours
                %M - two-digit number of whole minutes modulo 60
                %m - number of whole minutes
                %S - two-digit number of whole seconds modulo 60
                %s - number of whole seconds
                %f - six-digit fractional second
                %<n>f - n-digit fractional second, with 1 <= n <= 6
                %% - percent
            
            During formatting, each code is replaced with the information
            described for the time difference being formatted. Note that
            no rounding occurs during formatting. For example, formatting
            a time difference of 1.789 seconds according to the format
            string "%s" yields the string "1", and formatting it according
            to the format string "%1f" yields the string "7".
            
        """
        
        
        self._format_string = format_string
        
        self._literal_segments, self._parsed_format_codes = \
            self._parse_format_string(format_string)
        
        self._min_time_increment = self.get_min_time_increment(format_string)
    
    
    def _parse_format_string(self, format_string):
        literal_segments, format_codes = _parse_format_string(format_string)
        parsed_format_codes = [
            self._parse_format_code(c) for c in format_codes]
        return literal_segments, parsed_format_codes
    
    
    def _parse_format_code(self, format_code):
        
        char = format_code[-1]
        method_name = _FORMATTING_METHOD_NAMES.get(char, f'_format_{char}')
        method = getattr(self, method_name)
        
        # This yields the empty list for format codes with no arguments,
        # or a length-one list containing a digit for an "f" format code
        # with an argument.
        args = list(format_code)[:-1]
        
        return method, args
    
    
    @property
    def format_string(self):
        return self._format_string
    
    
    @property
    def min_time_increment(self):
        return self._min_time_increment
    
    
    def format(self, difference):
        
        """
        Formats the specified time difference.
        
        Parameters
        ----------
        difference : int or float
            the time difference to be formatted, in seconds.
        
        Returns
        -------
        str
            the formatted time difference.
        """
        
        
        formatted_segments = [
            method(difference, *args)
            for method, args in self._parsed_format_codes]
        
        # Append empty string so `formatted_segments` has same length
        # as `self._literal_segments`.
        formatted_segments.append('')
        
        # Interleave literal and formatted segments.
        segment_pairs = zip(self._literal_segments, formatted_segments)
        segments = itertools.chain.from_iterable(segment_pairs)
        
        return ''.join(segments)
    
    
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
    
    
    def _format_percent(self, _):
        return '%'


def _parse_format_string(format_string):
    parts = _FORMAT_CODE_RE.split(format_string)
    literal_segments = parts[::2]
    format_codes = parts[1::2]
    return literal_segments, format_codes
