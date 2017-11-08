"""Module containing class `ConditionalPrinter`."""


class ConditionalPrinter:
    
    """
    Callable that prints its argument to stdout if an only if a condition
    specified at initialization is `True`.
    """
    
    
    def __init__(self, condition):
        self._condition = condition
        
        
    def __call__(self, x):
        if self._condition:
            print(x)
