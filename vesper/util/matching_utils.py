"""Utility functions that match elements of two sequences."""


def match_intervals(
        source_intervals, target_intervals, intersection_threshold=0):
    
    """
    Matches intervals from two sequences, a *source sequence* and a
    *target sequence*, by assigning intervals of the source sequence
    to intervals of the target sequence.
    
    For each target interval, this function matches with it the first
    source interval that intersects it by at least the intersection
    threshold, and whose intersection with it is maximal. Note that
    in accordance with these criteria, a target interval may not
    match any source interval.
    
    Parameters
    ----------
    source_intervals : sequence of pairs of floats or ints
        Each interval is a pair of numbers, the start and end of the
        interval. The sequence of starts and the sequence of ends must
        both increase monotonically.
        
    target_intervals : sequence of pairs of floats or ints
        Each interval is a pair of numbers, the start and end of the
        interval. The sequence of starts and the sequence of ends must
        both increase monotonically.
        
    intersection_threshold : float, default 0
        Minimum required fractional intersection for two intervals to
        match. The fractional intersection of two intervals is the size
        of their intersection divided by the minimum of their sizes.
        
    Returns
    -------
    sequence of pairs of ints
        Pairs of indices of matching intervals. The first index of
        each pair is a source interval index, and the second index
        is a target interval index. Each the index of each target
        interval appears in at most one pair, with the index of the
        first source interval whose intersection with the target
        interval is at least the intersection threshold and is
        maximal. The pairs are ordered lexicographically.
    """
    
    matches = []
    
    source_interval_count = len(source_intervals)
    target_interval_count = len(target_intervals)
    
    i = 0
    j = 0
    
    while i != source_interval_count and j != target_interval_count:
        
        start_i, end_i = source_intervals[i]
        start_j, end_j = target_intervals[j]
        
        if end_i < start_j:
            # source interval i precedes target interval j
            
            i += 1
            
        elif end_j < start_i:
            # target interval j precedes source interval i
            
            j += 1
            
        else:
            # source interval i and target interval j intersect,
            # and source interval i is first source interval that
            # intersects target interval j
            
            best_i = _find_best_source_match(
                source_intervals, target_intervals, i, j,
                intersection_threshold)
            
            if best_i is not None:
                matches.append((best_i, j))
                
            j += 1
            
    return matches


def _find_best_source_match(
        source_intervals, target_intervals, i, j, intersection_threshold):
    
    """
    Given that source interval i is the first source interval that
    intersects target interval j, return the index of the first source
    interval that matches target interval j maximally, or `None` if
    there is no such source interval.
    
    A source interval is said to *match* a target interval iff the ratio
    of the duration of the intersection of the intervals to the minimum
    of their durations is at least `_DURATION_THRESHOLD`. A source
    interval matches a target interval *maximally* iff the ratio is the
    maximum of such ratios over all matching source intervals.
    """
    
    start_j, end_j = target_intervals[j]
    dur_j = end_j - start_j
        
    k = i
    best_k = None
    best_fraction = 0
    
    source_interval_count = len(source_intervals)
    
    while k != source_interval_count:
        
        start_k, end_k = source_intervals[k]
        
        if start_k >= end_j:
            # source interval k follows target interval j
            
            break
        
        else:
            # source interval k intersects target interval j
            
            dur_k = end_k - start_k
            intersection_start = max(start_k, start_j)
            intersection_end = min(end_k, end_j)
            intersection_dur = intersection_end - intersection_start
            min_dur = min(dur_k, dur_j)
            fraction = intersection_dur / min_dur
            
            if fraction >= intersection_threshold and fraction > best_fraction:
                # source interval k is better match for target interval j
                # than any preceding source interval
                
                best_k = k
                best_fraction = fraction
                
            k += 1
                
    return best_k
