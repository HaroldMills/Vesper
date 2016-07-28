"""
Utility functions concerning United States Naval Observatory (USNO) tables.
"""


from vesper.ephem.usno_altitude_azimuth_table import UsnoAltitudeAzimuthTable
from vesper.ephem.usno_rise_set_table import UsnoRiseSetTable


RISE_SET_TABLE_TYPES = (
    'Sunrise/Sunset',
    'Moonrise/Moonset',
    'Civil Twilight',
    'Nautical Twilight',
    'Astronomical Twilight'
)


ALTITUDE_AZIMUTH_TABLE_TYPES = (
    'Sun Altitude/Azimuth',
    'Moon Altitude/Azimuth'
)


TABLE_TYPES = RISE_SET_TABLE_TYPES + ALTITUDE_AZIMUTH_TABLE_TYPES


_TABLE_CLASSES = {
    'Sunrise/Sunset': UsnoRiseSetTable,
    'Moonrise/Moonset': UsnoRiseSetTable,
    'Civil Twilight': UsnoRiseSetTable,
    'Nautical Twilight': UsnoRiseSetTable,
    'Astronomical Twilight': UsnoRiseSetTable,
    'Sun Altitude/Azimuth': UsnoAltitudeAzimuthTable,
    'Moon Altitude/Azimuth': UsnoAltitudeAzimuthTable
}


_FILE_NAME_TABLE_TYPES = {
    'Sunrise/Sunset': 'Sunrise Sunset',
    'Moonrise/Moonset': 'Moonrise Moonset',
    'Sun Altitude/Azimuth': 'Sun Altitude Azimuth',
    'Moon Altitude/Azimuth': 'Moon Altitude Azimuth'
}
"""
Mapping from regular table type names to the table type names used in file
names.

This mapping is needed since some of the regular names include slashes,
which are not allowed in file names.
"""


_REGULAR_TABLE_TYPES = \
    dict((v, k) for k, v in _FILE_NAME_TABLE_TYPES.items())
"""
Mapping from the table type names used in file names to regular table type
names.

This is the inverse of the `FILE_NAME_TABLE_TYPES` mapping.
"""
   
    
def get_table_class(table_type):
    return _TABLE_CLASSES[table_type]
    
    
def download_table(table_type, *args):
    cls = get_table_class(table_type)
    function = getattr(cls, 'download_table_text')
    return function(table_type, *args)


def get_file_name_table_type(table_type):
    return _FILE_NAME_TABLE_TYPES.get(table_type, table_type)


def get_table_type(file_name_table_type):
    return _REGULAR_TABLE_TYPES.get(file_name_table_type, file_name_table_type)
