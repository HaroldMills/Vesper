"""Abstract clip figure superclass."""


class ClipFigure(object):
    
    
    def __init__(self, parent, figure):
        self._parent = parent
        self._figure = figure
        self._clip = None
                

    @property
    def parent(self):
        return self._parent
    
    
    @property
    def figure(self):
        return self._figure
    
    
    @property
    def canvas(self):
        return self.figure.canvas
    
    
    @property
    def clip(self):
        return self._clip
    
    
    @clip.setter
    def clip(self, clip):
        self._set_clip(clip)
        
        
    def _set_clip(self, clip):
        self._clip = clip
