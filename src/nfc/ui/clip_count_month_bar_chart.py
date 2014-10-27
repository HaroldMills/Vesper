from __future__ import print_function

import calendar
import datetime
import math

import matplotlib as mpl
mpl.rcParams['backend.qt4'] = 'PyQt4'
    
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt4.QtGui import QFrame
import numpy as np


class ClipCountMonthBarChart(QFrame):
    
    
    def __init__(self, parent, archive):
        
        super(ClipCountMonthBarChart, self).__init__(parent)
        
        self._archive = archive
        
        self._station_name = None
        self._detector_name = None
        self._clip_class_name = None
        self._year = None
        self._month = None
        
        self._plot_log_counts = False

#         self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        
        self._figure = Figure()
        self._set_figure_face_color()
       
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setParent(self)

        self._axes = self._figure.add_subplot(111)
#        self._axes = self._figure.add_axes([.05, .05, .9, .9])
             
        self._draw_chart()
        
#         connect = self._canvas.mpl_connect
#         connect('button_press_event', _on_button_press)
#         connect('button_release_event', _on_button_release)
#         connect('motion_notify_event', _on_motion_notify)
#         connect('figure_enter_event', _on_figure_enter)
#         connect('figure_leave_event', _on_figure_leave)
#         connect('axes_enter_event', _on_axes_enter)
#         connect('axes_leave_event', _on_axes_leave)


    def _set_figure_face_color(self):
        
        """
        Sets the face color of the figure to match the Qt palette
        window color.
        """
        
        c = self.palette().window().color()
        color = (c.red(), c.green(), c.blue(), c.alpha())
        
        # TODO: The color we get from the palette seems to be a little
        # darker than the actual window color (at least for Mac OS X),
        # so we apply the following empirically-derived "fix". Try to
        # figure out how to obviate this. Is the underlying problem
        # that Matplotlib and PyQt4 treat colors slightly differently?
        color = tuple(min(c / 249.5, 1) for c in color)
        
        self._figure.set_facecolor(color)
 
     
    @property
    def station_name(self):
        return self._station_name
    
    
    @property
    def detector_name(self):
        return self._detector_name
    
    
    @property
    def clip_class_name(self):
        return self._clip_class_name
    
    
    @property
    def year(self):
        return self._year
    
    
    @property
    def month(self):
        return self._month
    
    
    def configure(
            self, station_name, detector_name, clip_class_name, year, month):
        
        self._station_name = station_name
        self._detector_name = detector_name
        self._clip_class_name = clip_class_name
        self._year = year
        self._month = month
        
        self._draw_chart()
        
        
    def _draw_chart(self):
                
        axes = self._axes
        axes.cla()
        
        if self._station_name is not None:
            
            year = self.year
            month = self.month
            
            start_date = datetime.date(year, month, 1)
            (_, num_days) = calendar.monthrange(year, month)
            end_date = datetime.date(year, month, num_days)
            
            counts = self._archive.get_clip_counts(
                self.station_name, self.detector_name,
                start_date, end_date, self.clip_class_name)
            
            bottoms = np.zeros(num_days)
             
            width = .7
            widths = width * np.ones(num_days)
             
            heights = np.zeros(num_days, dtype='float')
            for date, count in counts.iteritems():
                heights[date.day - 1] = self._get_bar_height(count)
        
            lefts = np.arange(num_days) + .5 - width / 2
             
            axes = self._axes
             
            axes.barh(bottoms, widths, heights, lefts)
             
            tick_freq = 1
            num_ticks = num_days // tick_freq
            tick_indices = tick_freq * (np.arange(num_ticks) + 1)
            axes.set_xticks(tick_indices - .5)
            axes.set_xticklabels([str(i) for i in tick_indices])
            axes.set_xbound(0, num_days)
            
            axes.set_xlabel('Date')
            axes.set_ylabel(
                'Log10(Count)' if self._plot_log_counts else 'Count')
            
            clip_class_name = _prettify_clip_class_name(self.clip_class_name)
            title = '{:s} {:s} {:s} Counts, {:s} {:d}'.format(
                self.station_name, self.detector_name, clip_class_name,
                calendar.month_name[self.month], self.year)
            axes.set_title(title)
            
            self._canvas.draw()


    def _get_bar_height(self, count):
        if self._plot_log_counts:
            return 0 if count == 0 else math.log10(count)
        else:
            return count
            

    def resizeEvent(self, event):
        r = self.contentsRect()
        self._canvas.setGeometry(r.x(), r.y(), r.width(), r.height())
        
        
# TODO: Move this to `archive_utils` (but maybe this functionality
# should be per-archive)?
def _prettify_clip_class_name(name):
    if name.startswith('Call.'):
        return name[len('Call.'):]
    else:
        return name
