"""Module containing class `Multiselection`."""


# TODO: Perhaps switch implementation to one that manipulates a list
# of booleans, or a list of objects with `selected` properties. Or
# perhaps the constructor should accept a sequence of objects of any
# type and associate their IDs with booleans. There could be a listener
# that is called once for each change of state of an object, with the
# object and the new state.

# TODO: State saving and restoration.


class Multiselection(object):
    
    
    def __init__(self, min_index, max_index):
        self._min_index = min_index
        self._max_index = max_index
        self._intervals = []
        self._anchor_index = None
        self._anchor_interval_index = None
        
        
    @property
    def min_index(self):
        return self._min_index
    
    
    @property
    def max_index(self):
        return self._max_index
    
    
    @property
    def anchor_index(self):
        return self._anchor_index
    
    
    @property
    def selected_intervals(self):
        return tuple(self._intervals)
    
    
    def select(self, index):
        self._intervals = [(index, index)]
        self._anchor_index = index
        self._anchor_interval_index = 0
        
        
    def __contains__(self, index):
        return self._find_containing_interval(index) is not None
        
        
    def _find_containing_interval(self, index):
        
        for i, v in enumerate(self._intervals):
            if _contains(v, index):
                return i
            
        return None
            
             
    def extend(self, index):
        
        intervals = self._intervals
        
        if self._anchor_index is None:
            self._anchor_index = self._min_index
            intervals.append((self._min_index, index))
            
        else:
            
            i = self._anchor_interval_index
            
            if index <= self._anchor_index:
                intervals[i] = (index, self._anchor_index)
            else:
                intervals[i] = (self._anchor_index, index)
                
        self._normalize()
            
            
    def _normalize(self):
        
        """
        Normalizes the internal data structures of this selection.
        
        When this method is called:
        
        * The intervals of `self._intervals` may not be disjoint, and
          they may not be ordered by increasing start index.
        
        * `self._anchor_index` is what it should be, but
          `self._anchor_interval_index` is undefined.
          
        Upon return:
        
        * The intervals of `self._intervals` are disjoint and in
          order of increasing start index.
          
        * `self._anchor_index` is unchanged, and if it is not `None`,
          the interval `self._intervals[self._anchor_interval_index]`
          contains it.
        """
        
        
        old = self._intervals

        if len(old) > 0:
            
            old.sort()
            
            new = self._intervals = [old[0]]
            
            if _contains(new[-1], self._anchor_index):
                self._anchor_interval_index = len(new) - 1
                
            for w in old[1:]:
                
                v = new[-1]
                
                # Note that in the calls to `_combinable` and `_union`
                # the order of `v` and `w` matters.
                
                if _combinable(v, w):
                    new[-1] = _union(v, w)
                    
                else:
                    new.append(w)
                    
                if _contains(new[-1], self._anchor_index):
                    self._anchor_interval_index = len(new) - 1
            
            
    def toggle(self, index):
        
        intervals = self._intervals
        
        i = self._find_containing_interval(index)
        
        if i is None:
            # item to be toggled is not selected
            
            intervals.append((index, index))
            self._anchor_index = index
            self._normalize()
            
        else:
            # item to be toggled is selected
            
            a, b = intervals[i]

            if a != b:
                # part of interval will remain selected after item
                # `index` is deselected
                
                del intervals[i]
                
                if index == b:
                    
                    intervals.append((a, b - 1))
                    self._anchor_index = index - 1
                    
                else:
                    
                    if index != a:
                        intervals.append((a, index - 1))
                        
                    intervals.append((index + 1, b))
                    self._anchor_index = index + 1
                    
                self._normalize()
                
            else:
                # none of interval will remain selected after item
                # `index` is deselected
                
                if i != len(intervals) - 1:
                    # interval is not last selected interval
                    
                    self._anchor_index = intervals[i + 1][0]
                    
                elif i != 0:
                    # interval is last selected interval but another
                    # precedes it
                    
                    self._anchor_index = intervals[i - 1][1]
                    
                else:
                    # interval is only selected interval
                    
                    self._anchor_index = None
                    
                del intervals[i]
            
                
def _contains(v, i):
    return v[0] <= i and i <= v[1]


def _combinable(v, w):
    # Caller ensures that v[0] <= w[0].
    return v[1] >= w[0] - 1


def _union(v, w):
    # Caller ensures that v[0] <= w[0] and v[1] >= w[0]
    return (v[0], max(v[1], w[1]))
