"""
Module containing class `Named`.

A `Named` object is just an object with a name.
"""


class Named:
    
    """Named object."""
    
    
    def __init__(self, name):
        self._name = name
        
        
    def __eq__(self, other):
        return isinstance(other, Named) and self.name == other.name


    @property
    def name(self):
        return self._name
