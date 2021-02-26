"""Module containing class `DateTimeFormatter`."""


import itertools
import re


_FRACTION_CODE_RE = re.compile('%([1-6])f')
"""Regular expression for modified fraction codes."""

_FRACTION_PLACEHOLDER = '<~!@#$^&*>'
"""
Placeholder for modified fraction codes in `datetime.strftime` format string.

We replace modified fraction codes with this placeholder to make their
locations easy to find in the output of `datetime.strftime`.
"""

_FORMAT_CODE_RE = re.compile('%([HhIMmSsf%]|[1-6]f)')
"""
Regular expression for all format codes relevant to getting the minimum
time increment for a format string.
"""

_FORMAT_CODE_TIME_INCREMENTS = {
    'H': 3600,
    'h': 3600,
    'I': 3600,
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
}
"""
Mapping from format codes to minimum formatted time increments in seconds.
"""


class DateTimeFormatter:
    
    """Formats `datetime` objects according to a format string."""
    
    
    @staticmethod
    def get_min_time_increment(format_string):
        
        """
        Gets the minimum nonzero increment between two `datetime`
        objects as formatted with the specified format string.
        """
        
        
        # Split format string at double percents. This yields the
        # segments of the format string we need to search for format
        # codes. It's important to get rid of the double percents
        # so they don't interfere with the search for format codes.
        # Consider the format string "%%H", for example, which does
        # not indicate an hour but rather the string "%H".
        format_segments = format_string.split('%%')
        
        # Get minimum time increment for each format segment.
        increments = [_get_min_time_increment(s) for s in format_segments]
        
        # Exclude `None` time increments.
        increments = [i for i in increments if i is not None]
        
        if len(increments) == 0:
            return None
        else:
            return min(increments)
    
    
    def __init__(self, format_string):
        
        """
        Initializes a `datetime` formatter for the specified format string.
        
        Parameters
        ----------
        format_string : str
            the format according to which to format `datetime` objects.
            
            The format string can be any format string that one might
            pass to the `datetime.strftime` method, but one can also
            use the additional format code:
            
                %<n>f - n-digit fractional second, with 1 <= n <= 6
            
            As with `datetime.strftime`, during formatting each format
            code is replaced with the appropriate string for the
            `datetime` being formatted. Note that no rounding occurs
            during formatting. For example, formatting the `datetime`
            2020-01-01 12:34:56.789 according to the format code
            "%S" yields the string "6", and formatting it according
            to the format code "%1f" yields the string "7".
            
        """
        
        
        self._format_string = format_string
        
        self._strftime_format_string, self._digit_counts = \
            self._parse_format_string(format_string)
        
        self._min_time_increment = self.get_min_time_increment(format_string)
    
    
    def _parse_format_string(self, format_string):
        
        # Split format string at double percents. This yields the
        # segments of the format string we need to search for modified
        # fraction codes. It's important to get rid of the double percents
        # so they don't interfere with the search for modified fraction
        # codes. Consider the format string "%%3f", for example, which
        # does not indicate a fractional second but rather the string "%3f".
        format_segments = format_string.split('%%')
        
        # Replace modified fraction codes with placeholders, retaining
        # digit counts separately.
        pairs = [self._parse_format_segment(s) for s in format_segments]
        
        # Zip pairs into `strftime` format segments and digit counts.
        strftime_format_segments, digit_count_lists = zip(*pairs)
        
        # Join `strftime` format segments with double percents.
        strftime_format_string = '%%'.join(strftime_format_segments)
        
        # Flatten digit count lists.
        digit_counts = list(itertools.chain.from_iterable(digit_count_lists))
        
        return strftime_format_string, digit_counts
    
    
    def _parse_format_segment(self, format_segment):
        
        # Split format segment at modified fraction codes.
        parts = _FRACTION_CODE_RE.split(format_segment)
        
        # Deinterleave format subsegments and digit counts.
        format_subsegments = parts[::2]
        digit_counts = [int(d) for d in parts[1::2]]
        
        # Rejoin format subsegments with fraction placeholder.
        strftime_format_segment = \
            _FRACTION_PLACEHOLDER.join(format_subsegments)
        
        return strftime_format_segment, digit_counts
    
    
    @property
    def format_string(self):
        return self._format_string
    
    
    @property
    def min_time_increment(self):
        return self._min_time_increment
    
    
    def format(self, dt):
        
        """
        Formats the specified `datetime` object.
        
        Parameters
        ----------
        dt : datetime
            the `datetime` to be formatted.
        
        Returns
        -------
        str
            the formatted `datetime`.
        """
        
        
        # Format with `datetime.strftime`.
        formatted_datetime = dt.strftime(self._strftime_format_string)
        
        # Replace placeholders with fractional seconds.
        return self._add_fractional_seconds(
            formatted_datetime, self._digit_counts, dt)
    
    
    def _add_fractional_seconds(self, formatted_datetime, digit_counts, dt):
        
        # Split formatted `datetime` at fraction placeholder.
        other_segments = formatted_datetime.split(_FRACTION_PLACEHOLDER)
        
        # Create fraction segments to substitute for placeholders.
        microsecond = f'{dt.microsecond:06d}'
        fraction_segments = [microsecond[:c] for c in digit_counts]
        
        # Append empty string so `fraction_segments` has same length
        # as `other_segments`.
        fraction_segments.append('')
        
        # Interleave two types of segments.
        pairs = zip(other_segments, fraction_segments)
        segments = itertools.chain.from_iterable(pairs)
        
        return ''.join(segments)


def _get_min_time_increment(format_segment):
    
    # Get format codes of format segment.
    parts = _FORMAT_CODE_RE.split(format_segment)
    format_codes = parts[1::2]
    
    # Get format code increments.
    increments = [_FORMAT_CODE_TIME_INCREMENTS[c] for c in format_codes]
    
    if len(increments) == 0:
        return None
    else:
        return min(increments)
