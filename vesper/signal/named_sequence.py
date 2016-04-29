from collections.abc import Sequence


class NamedSequence(Sequence):
    
    
    def __init__(self, items=None):
        
        if items is None:
            items = []
            
        self._tuple = tuple(items)
        self._dict = dict((i.name, i) for i in items)
        self._names = tuple(i.name for i in items)
        
        
    def __len__(self):
        return len(self._tuple)
    
    
    def __getitem__(self, i):
        
        if isinstance(i, str):
            try:
                return self._dict[i]
            except KeyError:
                raise IndexError('name "{}" not found'.format(i))
            
        else:
            try:
                return self._tuple[i]
            except IndexError:
                raise IndexError('index {} out of range'.format(i))


    @property
    def names(self):
        return self._names