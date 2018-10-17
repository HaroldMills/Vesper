"""
Path converter for object names.

A name is a sequence of one or more characters. Each character can be
anything except for a newline.
"""


class NameConverter:
    
    regex = '.+'
    
    def to_python(self, value):
        return value
    
    def to_url(self, value):
        return value
