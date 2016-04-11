"""Utility functions pertaining to text."""


def quote_if_needed(s):
    if s.find(' ') != -1:
        return '"' + s + '"'
    else:
        return s
    
    
def format_number(x):
    
    # Formats a nonnegative number either as an integer if it rounds to
    # at least ten, or as a decimal rounded to two significant digits.
    
    if x == 0:
        return '0'
    
    else:
        
        i = int(round(x))
        
        if i < 10:
            
            # Get `d` as decimal rounded to two significant digits.
            
            xx = x
            n = 0
            while xx < 10:
                xx *= 10
                n += 1
            f = '{:.' + str(n) + 'f}'
            return f.format(x)
    
        else:
            return str(i)
    
    
