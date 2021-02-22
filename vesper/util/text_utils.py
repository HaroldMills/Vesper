"""Utility functions pertaining to text."""


from vesper.util.datetime_formatter import DateTimeFormatter
from vesper.util.time_difference_formatter import TimeDifferenceFormatter


def create_string_item_list(items):
    
    """
    Creates a human-readable string for a list of items.
    
    Examples:
    
        [] -> ''
        ['one'] -> 'one'
        ['one', two'] -> 'one and two'
        ['one', 'two', 'three'] -> 'one, two, and three'
        ['one', 'two', 'three', 'four'] -> 'one, two, three, and four'
        [1, 2, 3] -> '1, 2, and 3'
    """
    
    items = [str(i) for i in items]
    
    n = len(items)
    
    if n == 0:
        return ''
    
    elif n == 1:
        return items[0]
    
    elif n == 2:
        return items[0] + ' and ' + items[1]
    
    else:
        final_item = 'and ' + items[-1]
        return ', '.join(items[:-1] + [final_item])


def format_number(x):
    
    """
    Formats a nonnegative number either as an integer if it rounds to
    at least ten, or as a decimal rounded to two significant digits.
    """
    
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


def format_datetime(dt, format_string):
    formatter = DateTimeFormatter(format_string)
    return formatter.format(dt)


def format_time_difference(difference, format_string):
    formatter = TimeDifferenceFormatter(format_string)
    return formatter.format(difference)


def create_count_text(count, singular_units_text, plural_units_text=None):
    units = create_units_text(count, singular_units_text, plural_units_text)
    return '{} {}'.format(count, units)


def create_units_text(quantity, singular_units_text, plural_units_text=None):
    
    if quantity == 1:
        return singular_units_text
    
    elif plural_units_text is not None:
        return plural_units_text
    
    else:
        return singular_units_text + 's'
