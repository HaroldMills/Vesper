"""Module containing `LinearMapping` class."""


from vesper.signal.value_mapping import ValueMapping


class LinearMapping(ValueMapping):
    
    
    def __init__(self, a=1, b=0):
        super().__init__()
        self._a = float(a)
        self._b = float(b)
        
        
    def __eq__(self, other):
        if not isinstance(other, LinearMapping):
            return False
        else:
            return self.a == other.a and self.b == other.b
        
        
    @property
    def a(self):
        return self._a
    
    
    @property
    def b(self):
        return self._b
    
    
    def map(self, x):
        return self.a * x + self.b
    
    
    def invert(self, y):
        return (y - self.b) / self.a
    