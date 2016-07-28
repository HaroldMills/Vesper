"""Module containing class `IndexedAxis`."""


from vesper.signal.axis import Axis


'''
a.name                   # e.g. 'Time', 'Frequency'
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes

a.start_index            # start of index range
a.end_index              # end of index range, `None` if length zero
a.length                 # axis length in indices
'''


class IndexedAxis(Axis):
    
    
    def __init__(self, name=None, units=None, start_index=0, length=0):
        super().__init__(name, units)
        self._start_index = start_index
        self._length = length
        
        
    def __eq__(self, other):
        return isinstance(other, IndexedAxis) and \
            Axis.__eq__(self, other) and \
            self.start_index == other.start_index and \
            self.length == other.length
                   
                   
    @property
    def start_index(self):
        return self._start_index
    
    
    @property
    def end_index(self):
        if self.length == 0:
            return None
        else:
            return self.start_index + self.length - 1
    
    
    @property
    def length(self):
        return self._length
