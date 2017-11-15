"""Utility functions pertaining to NumPy arrays."""


import numpy as np


def find(x, y, tolerance=0):
    
    """
    Finds all occurrences of one one-dimensional array in another.
    
    The algorithm employed by this function is efficient when there are
    few occurrences of a small prefix of the first array in the second.
    It is inefficient in other cases.
    
    Parameters:
    
        x : one-dimensional NumPy array
            the array to be searched for.
            
        y: one-dimensional NumPy array
            the array to be searched in.
            
    Returns:
        NumPy array of starting indices of all occurrences of `x` in `y`.
    """

    m = len(x)
    n = len(y)
    
    if m == 0:
        return np.arange(n)
    
    else:
        # x has at least one element
        
        # Find indices i of x[0] in y[:n - m + 1]. These are the indices in y
        # where matches of x might start.
        diffs = np.abs(y[:n - m + 1] - x[0])
        i = np.where(diffs <= tolerance)[0]
        
        for k in range(1, m):
            # loop invariant: matches of x[:k] start at indices i in y
            
            if len(i) <= 1:
                # zero or one matches of x[:k] in y
                break
            
            # Find indices j of x[k] in y[i + k]. These are the indices
            # in i of the indices in y where matches of x[:k + 1] start. 
            diffs = np.abs(y[i + k] - x[k])
            j = np.where(diffs <= tolerance)[0]
            
            i = i[j]
        
        if len(i) == 1:
            # might have looked for only initial portion of x
            
            p = i[0]
            diffs = np.abs(y[p:p + m] - x)
            if np.all(diffs <= tolerance):
                return i
            else:
                return np.array([], dtype='int64')
        
        else:
            # i is the answer
            
            return i


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
