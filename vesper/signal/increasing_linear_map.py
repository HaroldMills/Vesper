"""Module containing class `IncreasingLinearMap`."""


from vesper.signal.invertible_map import InvertibleMap


class IncreasingLinearMap(InvertibleMap):
    
    
    def __init__(self, a=1, b=0):
        
        super().__init__()
        
        if a <= 0:
            raise ValueError(
                'Scale factor must be positive for increasing linear map.')
        
        self._a = a
        self._b = b
        
        self._inverse = None
        
        
    def __eq__(self, other):
        return isinstance(other, IncreasingLinearMap) and \
            self.a == other.a and \
            self.b == other.b
        
        
    @property
    def a(self):
        return self._a
    
    
    @property
    def b(self):
        return self._b
    
    
    def __call__(self, x):
        return self.a * x + self.b
    
    
    @property
    def inverse(self):
        if self._inverse is None:
            self._inverse = IncreasingLinearMap(1 / self.a, -self.b / self.a)
        return self._inverse
