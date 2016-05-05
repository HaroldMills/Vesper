"""Module containing `Axis` class."""


from vesper.util.bunch import Bunch
from vesper.util.named import Named


'''
a.name                   # e.g. 'Time', 'Frequency'
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes
'''


_DEFAULT_UNITS = Bunch(plural=None, singular=None, abbreviation=None)


class Axis(Named):
    
    
    def __init__(self, name=None, units=None):
        
        super().__init__(name)
        
        if units is None:
            self._units = _DEFAULT_UNITS
        else:
            self._units = Bunch(units)
        
        
    def __eq__(self, other):
        return isinstance(other, Axis) and \
            self.name == other.name and \
            self.units == other.units


    @property
    def units(self):
        return self._units
