import numpy as np


_STATION_NAMES = '''
Angela
Bear
Bell Crossing
Darby
Dashiell
Davies
Deer Mountain
Floodplain
Florence
KBK
Lilo
MPG North
Nelson
Oxbow
Powell
Reed
Ridge
Seeley
Sheep Camp
St Mary
Sula Peak
Teller
Troy
Walnut
Weber
Willow
'''.split()


_COUNTS = np.array([
    281819,  # Angela
    83224,   # Bear
    35904,   # Bell Crossing
    194767,  # Darby
    39284,
    160417,
    86024,
    86379,
    71937,
    60296,
    114251,
    728656,
    204924,
    655681,
    85147,
    42794,
    160442,
    48952,
    39174,
    176465,
    73846,
    60300,
    105118,
    33572,
    146655,
    91411
])


def main():
    
    counts = get_delete_clips_retain_counts(_COUNTS, 500000)
    
    print('counts', counts)
    print('sum', counts.sum())
    
    pairs = zip(_STATION_NAMES, counts)
    for station_name, count in pairs:
        print('{}: {}'.format(station_name, count))
    
    
def get_delete_clips_retain_counts(counts, desired_total_count):
    
    if counts.sum() <= desired_total_count:
        # have no clips to spare
        
        return counts
    
    else:
        # have clips to spare
        
        lower = 0
        upper = desired_total_count + 1
        
        # Loop invariant:
        # _get_clipped_sum(counts, lower) <= desired_total_count and
        # _get_clipped_sum(counts, upper) > desired_total_count
        
        while upper != lower + 1:
            
            # _show_clipped_sums(counts, lower, upper)
            
            middle = (lower + upper) // 2
            
            middle_sum = _get_clipped_sum(counts, middle)
            
            if middle_sum > desired_total_count:
                upper = middle
            else:
                lower = middle
                
        # _show_clipped_sums(counts, lower, upper)
        
        # Get indices where counts exceed `lower`.
        indices = np.argwhere(counts > lower)
        
        # Clip counts to `lower`
        counts = counts.clip(0, lower)
        
        # Discard unneeded indices.
        indices = indices[:desired_total_count - counts.sum()]
        
        # Increment maximal counts to reach desired total count.
        counts[indices] += 1
        
        return counts
            
             
def _show_clipped_sums(counts, lower, upper):
    _show_clipped_sum('lower', counts, lower)
    _show_clipped_sum('upper', counts, upper)
    print()
    
   
def _show_clipped_sum(name, counts, limit):
    clipped_sum = _get_clipped_sum(counts, limit)
    print(name, limit, clipped_sum)
                
        
def _get_clipped_sum(counts, limit):
    return counts.clip(0, limit).sum() 
        
    
if __name__ == '__main__':
    main()
