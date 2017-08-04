"""Module containing functions pertaining to clip counts."""


def get_bird_count(times, count_suppression_interval):
    
    """
    Estimates the number of birds of a particular type (either a species
    or a species complex) from the start times of their call clips.
    
    The counting algorithm considers each of the times in order. The call
    of a particular time is considered to be from a new bird if and only
    if the time is either the first time or at least
    `count_suppression_interval` seconds have passed since the last time
    whose call was considered to be from a new bird.
    """
    
    if len(times) == 0:
        return 0
    
    else:
        # have at least one time
        
        last_time = times[0]
        count = 1
        
        for time in times[1:]:
            
            if time - last_time >= count_suppression_interval:
                count += 1
                last_time = time
                
        return count
