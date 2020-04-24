"""Module containing class `InvertibleMap`."""


class InvertibleMap:


    def __call__(self, x):
        raise NotImplementedError()
    
    
    @property
    def inverse(self):
        raise NotImplementedError()
