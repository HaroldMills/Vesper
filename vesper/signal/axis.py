"""Module containing `Axis` class."""


from .linear_mapping import LinearMapping
from vesper.util.named import Named


'''
a.name                   # e.g. "Time", "Frequency", "Bearing"
a.units                  # e.g. "seconds", "hertz"
a.units_abbreviation     # e.g. "S", "Hz"

a.start_index            # start of index range, `None` if length zero
a.end_index              # end of index range, `None` if length zero
a.length                 # axis length in indices

a.start_value            # value at start index, `None` if length zero
a.end_value              # value at end index, `None` if length zero
a.span                   # end value less start value, `None` if length zero

a.index_to_value_mapping         # invertible mapping
a.index_to_value(indices)        # indices may be float
a.value_to_index(values)         # indices are float
'''


class Axis(Named):
    
    
    def __init__(
            self, name='', units='', units_abbreviation='', start_index=0,
            length=0, index_to_value_mapping=LinearMapping()):
        
        super().__init__(name)

        self._units = units
        self._units_abbreviation = units_abbreviation
        self._start_index = start_index
        self._length = length
        self._index_to_value_mapping = index_to_value_mapping
        
        
    @property
    def units(self):
        return self._units
    
    
    @property
    def units_abbreviation(self):
        return self._units_abbreviation


    @property
    def start_index(self):
        if self.length == 0:
            return None
        else:
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
    
    
    @property
    def start_value(self):
        if self.length == 0:
            return None
        else:
            return self.index_to_value(self.start_index)
    
    
    @property
    def end_value(self):
        if self.length == 0:
            return None
        else:
            return self.index_to_value(self.end_index)
    
    
    @property
    def span(self):
        if self.length == 0:
            return None
        else:
            return self.end_value - self.start_value


    @property
    def index_to_value_mapping(self):
        return self._index_to_value_mapping
    
    
    def index_to_value(self, indices):
        return self._index_to_value_mapping.map(indices)
    
    
    def value_to_index(self, values):
        return self._index_to_value_mapping.invert(values)
