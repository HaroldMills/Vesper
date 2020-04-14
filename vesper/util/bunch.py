"""Module containing class `Bunch`."""


# TODO: Would it make sense for this to subclass `dict` but override the
# initializer and all methods that accept keys? We should check that all
# keys that make it into a `Bunch` are valid Python identifiers.


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
        
        
    def __len__(self, key):
        return len(self.__dict__)
    
    
    def __contains__(self, key):
        return key in self.__dict__
    
    
    def __iter__(self):
        return self.__dict__.__iter__()
    
    
    def get(self, key, default=None):
        return self.__dict__.get(key, default)
