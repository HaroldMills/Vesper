"""
Utility functions concerning clip imports.

The function of this module used to be in the `clip_importer` module,
but I moved it here to make it easier to run its unit tests.
"""


import datetime
import re

from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


_FILE_NAME_REGEX = re.compile(
    r'^'
    r'(?P<detector_name>[^_]+)'
    r'_'
    r'(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)'
    r'_'
    r'(?P<hour>\d\d)\.(?P<minute>\d\d)\.(?P<second>\d\d)'
    r'_'
    r'(?P<num>\d\d)'
    r'\.wav'
    r'$')


def parse_clip_file_name(file_name):
    
    m = _FILE_NAME_REGEX.match(file_name)
    
    if m is not None:
        
        m = Bunch(**m.groupdict())
        
        try:
            start_time = time_utils.parse_date_time(
                m.year, m.month, m.day, m.hour, m.minute, m.second)
        except Exception as e:
            raise ValueError(
                'Could not get start time from file name: {}'.format(str(e)))
        
        tenths = datetime.timedelta(microseconds=100000 * int(m.num))
        start_time += tenths
        
        return m.detector_name, start_time
        
    else:
        raise ValueError('Could not parse file name.')


