"""Module containing `SampleArrayAxis` class."""


from vesper.signal.index_axis import IndexAxis
from vesper.signal.linear_mapping import LinearMapping


'''
a.name                   # e.g. "Frequency", "Bearing"
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes

a.start_index            # start of index range
a.end_index              # end of index range, `None` if length zero
a.length                 # axis length in indices

a.index_to_value_mapping
a.index_to_value(i)      # indices may be float
a.value_to_index(v)      # indices are float

a.start_value            # value at start index
a.end_value              # value at end index, `None` if length zero
a.span                   # end value less start value, `None` if length zero
'''


class SampleArrayAxis(IndexAxis):
    
    
    def __init__(
            self, name=None, units=None, length=0, index_to_value_mapping=None):
        
        super().__init__(name, units, 0, length)

        if index_to_value_mapping is None:
            self._index_to_value_mapping = LinearMapping()
        else:
            self._index_to_value_mapping = index_to_value_mapping


    def __eq__(self, other):
        return isinstance(other, SampleArrayAxis) and \
            IndexAxis.__eq__(self, other) and \
            self.index_to_value_mapping == other.index_to_value_mapping
                   

    @property
    def index_to_value_mapping(self):
        return self._index_to_value_mapping
    
    
    def index_to_value(self, indices):
        return self._index_to_value_mapping.map(indices)
    
    
    def value_to_index(self, values):
        return self._index_to_value_mapping.invert(values)
        
        
    @property
    def start_value(self):
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
