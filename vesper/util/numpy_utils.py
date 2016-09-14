import numpy as np


def find(x, y):
    
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
        list of starting indices of all occurrences of `x` in `y`.
    """
    
    m = len(x)
    n = len(y)
    
    if m == 0:
        return np.arange(n)
    
    else:
        # x has at least one element
        
        # Find indices i of x[0] in y[:n - m + 1]. These are the indices in y
        # where matches of x might start.
        i = np.where(y[:n - m + 1] == x[0])[0]
        
        for k in range(1, m):
            # loop invariant: matches of x[:k] start at indices i in y
            
            if len(i) <= 1:
                # zero or one matches of x[:k] in y
                break
            
            # Find indices j of x[k] in y[i + k]. These are the indices
            # in i of the indices in y where matches of x[:k + 1] start. 
            yy = y[i + k]
            j = np.where(yy == x[k])[0]
            
            i = i[j]
        
        if len(i) == 1:
            # might have looked for only initial portion of x
            
            return i if np.all(y[i[0]:i[0] + m] == x) else []
        
        else:
            # i is the answer
            
            return i
