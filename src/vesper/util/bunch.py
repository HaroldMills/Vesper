class Bunch(object):
    
    def __init__(self, *args, **kwargs):
        
        for arg in args:
            self.__dict__.update(arg.__dict__)
            
        self.__dict__.update(kwargs)
