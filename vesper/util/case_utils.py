"""Utility function for converting from snake case to camel case."""


def snake_to_camel(x):
    
    """
    Converts dictionary keys in the specified data from snake to camel case.
    
    The specified data can be `None` or a boolean, number, string, tuple,
    list, or dictionary. The conversion is recursive in that it includes
    the keys of dictionaries nested inside of dictionaries, tuples, or
    lists. All dictionary keys are assumed to be strings.
    """
    
    if isinstance(x, dict):
        return dict(
            (_key_to_camel(k), snake_to_camel(v))
            for k, v in x.items())
        
    elif isinstance(x, tuple):
        return tuple(snake_to_camel(i) for i in x)
    
    elif isinstance(x, list):
        return [snake_to_camel(i) for i in x]
    
    else:
        return x
    
    
def _key_to_camel(k):
    parts = k.split('_')
    parts = [parts[0].lower()] + [p.lower().capitalize() for p in parts[1:]]
    return ''.join(parts)
    