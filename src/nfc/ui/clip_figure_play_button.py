"""Play button for use in clip figures."""


from __future__ import print_function

from matplotlib.patches import Polygon
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredDrawingArea
import numpy as np


class ClipFigurePlayButton(object):
    
    
    DEFAULT_WIDTH = 17
    DEFAULT_HEIGHT = 17
    
    DEFAULT_UP_COLOR = (0, .9, 0)
    DEFAULT_DOWN_COLOR = (0, .6, 0)
    DEFAULT_BORDER_COLOR = (.2, .2, .2)


    def __init__(
        self,
        clip_figure,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        up_color=DEFAULT_UP_COLOR,
        down_color=DEFAULT_DOWN_COLOR,
        border_color=DEFAULT_BORDER_COLOR
    ):
        
        super(ClipFigurePlayButton, self).__init__()
        
        self.clip_figure = clip_figure
        self.width = width
        self.height = height
        self.up_color = up_color
        self.down_color = down_color
        self.border_color = border_color
        
        self._create_artists()
        
        self.reset()
        
        
    def _create_artists(self):
        
        w = self.width
        h = self.height
        
        # Create anchored drawing area.
        self._ada = AnchoredDrawingArea(
                        w, h, 0, 0, loc=2, pad=0, frameon=False)
        
        # Create triangle.
        path = np.array([[0, h], [w, h / 2.], [0, 0]])
        self._triangle = Polygon(path, edgecolor=self.border_color)
        
        # Put triangle in anchored drawing area.
        self._ada.drawing_area.add_artist(self._triangle)
        
        # Put anchored drawing area in figure axes.
        self.clip_figure._axes.add_artist(self._ada)
        
        
    def reset(self):
        self.visible = False
        self.down = False
        
    
    @property
    def visible(self):
        return self._ada.visible()
    
    
    @visible.setter
    def visible(self, visible):
        self._ada.set_visible(visible)
        self.clip_figure.canvas.draw()
        
        
    @property
    def down(self):
        return self._down
    
    
    @down.setter
    def down(self, down):
        self._down = down
        self._set_color(self.down_color if down else self.up_color)
        
        
    def _on_figure_enter(self, event):
        self.visible = True
#        print('ClipFigurePlayButton._on_figure_enter')
    
    
    def _on_figure_leave(self, event):
        self.visible = False
#        print('ClipFigurePlayButton._on_figure_leave')
   
    
    def _on_button_press(self, event):
        
        if event.button == 1 and self._contains(event):
            self.down = True
            
#        print('ClipFigurePlayButton._on_button_press')
            
            
    def _contains(self, event):
        return self._ada.contains(event)[0]
    
    
    def _set_color(self, color):
        self._triangle.set_facecolor(color)
        self.clip_figure.canvas.draw()
        

    def _on_button_release(self, event):
        
        if event.button == 1:
            
            if self.down:

                if self._contains(event):
                    self.clip_figure.clip.play()
                
                self.down = False
                
#        print('ClipFigurePlayButton._on_button_release')
