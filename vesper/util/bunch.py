"""Module containing class `Bunch`."""


class Bunch:
    
    
    def __init__(self, *args, **kwargs):
        
        for arg in args:
            self.__dict__.update(arg.__dict__)
            
        self.__dict__.update(kwargs)
        
        
    def __eq__(self, other):
        if not isinstance(other, Bunch):
            return False
        else:
            return self.__dict__ == other.__dict__
