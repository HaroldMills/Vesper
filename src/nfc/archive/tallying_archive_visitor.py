"""
This module contains old code from which a tallying clip archive visitor
could be constructed.
"""
        

from collections import defaultdict


def _tally(station_name, day, subdirs, info, tally):
    days = tally.setdefault(station_name, {})
    counts = days.setdefault(day, {})
    counts.setdefault(subdirs[0], 0)
    counts[subdirs[0]] += 1
    
        
_DELIMITER = '\t'


def _show_tally(tally):
    
    all_class_names = list(_get_class_names(tally))
    all_class_names.sort()
    
    print _DELIMITER.join(['Station', 'Date'] + all_class_names)
    
    total_counts = defaultdict(int)
    
    station_names = tally.keys()
    station_names.sort()
    
    for station_name in station_names:
        
        date_classes = tally[station_name]
        
        dates = date_classes.keys()
        dates.sort()
        
        for date in dates:
            
            class_counts = date_classes[date]
            
            class_names = class_counts.keys()
            class_names.sort()
            
            for name in class_names:
                count = class_counts[name]
                total_counts[name] += count
                
            columns = [station_name, date] + \
                      [str(class_counts.get(name, 0))
                       for name in all_class_names]
                
            print _DELIMITER.join(columns)
            
    columns = ['Total', ''] + \
              [str(total_counts[name]) for name in all_class_names]
    print _DELIMITER.join(columns)
            
        
def _get_class_names(tally):
    
    class_names = set()
    
    for date_classes in tally.itervalues():
        for class_counts in date_classes.itervalues():
            class_names |= set(class_counts.iterkeys())
                
    return class_names
