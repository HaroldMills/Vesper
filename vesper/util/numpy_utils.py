"""Utility functions pertaining to NumPy arrays."""


import numpy as np


def arrays_equal(x, y):
    
    """
    Tests if two arrays have the same shape and values.
    
    Parameters
    ----------
    x : NumPy array
        the first array
    y : NumPy array
        the second array
        
    Returns
    -------
    bool
        `True` if and only if `x` and `y` have the same shape and values.
        Note that two arrays of different dtypes can be equal as long as
        their values are equal.
    """
    
    # We check shapes before calling np.all since np.all broadcasts its
    # arguments as needed but we don't want it to. We want, for example,
    # for np.zeros(1) to *not* equal np.zeros(2).
    
    if x.shape != y.shape:
        return False
    else:
        return np.all(x == y)
    
    
def arrays_close(x, y):
    
    """
    Tests if two arrays have the same shape and close values.
    
    Parameters
    ----------
    x : NumPy array
        the first array
    y : NumPy array
        the second array
        
    Returns
    -------
    bool
        `True` if and only if `x` and `y` have the same shape and close
        values. The closeness of values is tested by calling `np.allclose`.
        Note that two arrays of different dtypes can be close as long as
        their values are close.
    """
    
    # We check shapes before calling np.all since np.all broadcasts its
    # arguments as needed but we don't want it to. We want, for example,
    # for np.zeros(1) to *not* be close to np.zeros(2).
    
    if x.shape != y.shape:
        return False
    else:
        return np.allclose(x, y)
    
    
def reproducible_choice(x, size=None, replace=True, p=None):
    
    """
    Like NumPy's `random.choice`, but always returns the same thing for
    the same arguments.
    """
    
    return _rs().choice(x, size, replace, p)


def _rs():
    return np.random.RandomState(seed=1)


def reproducible_permutation(x):
    
    """
    Like NumPy's `random.permutation`, but always returns the same thing
    for a given argument.
    """
    
    return _rs().permutation(x)


def reproducible_shuffle(x):
    
    """
    Like NumPy's `random.shuffle`, but always has the same effect on a
    given argument.
    """
    
    _rs().shuffle(x)
