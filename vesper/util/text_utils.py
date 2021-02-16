"""Utility functions pertaining to text."""


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


def format_time_difference(
        seconds, hours_digit_count=None, fraction_digit_count=0):
    
    # Get format for hours and minutes part of time difference.
    if hours_digit_count is None:
        hours_format = '{:d}'
    else:
        hours_format = '{:0' + str(hours_digit_count) + '}'
    hours_minutes_format = hours_format + ':{:02d}'
    
    # Get format for seconds part of time difference, including
    # fraction (if present).
    seconds_format = f'{{:.{fraction_digit_count}f}}'
    
    # Get sign prefix.
    if seconds < 0:
        seconds = -seconds
        prefix = '-'
    else:
        prefix = ''
    
    # Format hours and minutes.
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    hours_minutes = hours_minutes_format.format(hours, minutes)
    
    # Format integer and fractional parts of seconds together to
    # get appropriate rounding.
    seconds = seconds_format.format(seconds)
    
    # Split integer part and fractional part (if present) to handle
    # separately below.
    parts = seconds.split('.')
    
    # Pad seconds with zero on left if needed.
    seconds = parts[0].rjust(2, '0')
    
    # Get fraction (if present).
    if len(parts) == 1:
        fraction = ''
    else:
        fraction = '.' + parts[1]
    
    return f'{prefix}{hours_minutes}:{seconds}{fraction}'


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
