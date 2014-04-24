"""Utility functions pertaining to clip archives."""


def get_year_month_pairs(archive):
    
    pair = _get_pair(archive.get_start_night())
    endPair = _increment_pair(_get_pair(archive.get_end_night()))
    
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
