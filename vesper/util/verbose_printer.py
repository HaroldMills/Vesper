"""Module containing class `VerbosePrinter`."""


class VerbosePrinter:
    
    """
    Callable that prints its argument to stdout if an only if it has
    been configured to be verbose.
    """
    
    
    def __init__(self, verbose):
        self._verbose = verbose
        
        
    def __call__(self, x):
        if self._verbose:
            print(x)
