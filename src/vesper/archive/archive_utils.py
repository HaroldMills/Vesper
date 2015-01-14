"""
Utility functions pertaining to clip archives.

This module contains only functions that are not used by the `Archive`
class and related classes, including for example the `Station` and
`Detector` classes. For functions that are shared among the `Archive`
class and related classes, see the `archive_shared` module.

Because these functions are not used by the `Archive` class and related
classes, this module can import any of these classes at the top level
without causing import cycles.
"""


from vesper.archive.archive import Archive


def get_year_month_pairs(archive):
    
    pair = _get_pair(archive.start_night)
    endPair = _increment_pair(_get_pair(archive.end_night))
    
    pairs = []

    while pair != endPair:
        pairs.append(pair)
        pair = _increment_pair(pair)
        
    return pairs
    
    
def _get_pair(date):
    return (date.year, date.month)


def _increment_pair(pair):
    
    (year, month) = pair
    
    month += 1
    if month == 13:
        month = 1
        year += 1
        
    return (year, month)


def get_clip_class_name_options(archive):
    names = [s.name for s in archive.clip_classes] + \
            [Archive.CLIP_CLASS_NAME_UNCLASSIFIED]
    names += _create_wildcard_clip_class_names(names)
    names.sort()
    return names


def _create_wildcard_clip_class_names(names):
    
    separator = Archive.CLIP_CLASS_NAME_COMPONENT_SEPARATOR
    wildcard = Archive.CLIP_CLASS_NAME_WILDCARD
    
    wildcard_names = set([wildcard])
    
    for name in names:
        
        components = name.split(separator)
        
        if len(components) > 1:
            
            for i in xrange(len(components) - 1):
                t = separator.join(components[:i + 1]) + wildcard
                wildcard_names.add(t)
                
    return wildcard_names
