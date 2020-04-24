from collections.abc import Sequence


class NamedSequence(Sequence):
    
    
    def __init__(self, items=None):
        
        if items is None:
            items = []
            
        self._tuple = tuple(items)
        self._dict = dict((i.name, i) for i in items)
        self._names = tuple(i.name for i in items)
        
        
    def __eq__(self, other):
        return isinstance(other, NamedSequence) and \
            self._tuple == other._tuple
            
            
    def __len__(self):
        return len(self._tuple)
    
    
    def __getitem__(self, i):
        
        if isinstance(i, str):
            try:
                return self._dict[i]
            except KeyError:
                raise IndexError(f'Name "{i}" not found.')
            
        else:
            try:
                return self._tuple[i]
            except IndexError:
                raise IndexError(f'Index {i} out of range.')


    @property
    def names(self):
        return self._names
