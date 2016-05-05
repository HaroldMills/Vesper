"""Module containing `ValueMapping` class."""


class ValueMapping(object):
    
    
    def map(self, x):
        raise NotImplementedError()
    
    
    def invert(self, y):
        raise NotImplementedError()
