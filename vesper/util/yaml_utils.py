import dateutil.parser
import pytz
import yaml


def timestamp_constructor(loader, node):
    
    """
    Constructor for timestamps that uses `dateutil.parser.parse`.
    
    There are two problems with the default PyYAML timestamp constructor:
    
    1. It yields either a `datetime.date` object or a `datetime.datetime`
       object, depending on the parsed text. I would like for the constructor
       to always yield a `datetime.datetime` object.
       
    2. When it yields a `datetime.datetime` object, the object is always
       naive: any time zone information provided in the parsed string is
       ignored.
       
    These problems are resolved with this timestamp constructor. The
    constructor always returns a `datetime.datetime` object, and it
    returns a UTC time when the parsed text includes time zone information.
    The time zone of the UTC time is `pytz.utc`.
    """
    
    dt = dateutil.parser.parse(node.value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(pytz.utc)
    return dt


yaml.add_constructor('tag:yaml.org,2002:timestamp', timestamp_constructor)


# We use this function rather than invoking `yaml.load` directly from
# other modules so that our timestamp constructor is used rather than
# the default.
def load(*args):
    return yaml.load(*args)
    