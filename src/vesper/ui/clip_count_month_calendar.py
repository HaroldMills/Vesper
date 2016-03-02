from __future__ import print_function

import calendar
import datetime
import platform

import matplotlib as mpl
mpl.rcParams['backend.qt4'] = 'PyQt4'
    
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt4.QtCore import QSize
from PyQt4.QtGui import QFrame, QSizePolicy
import numpy as np

from vesper.util.notifier import Notifier
import vesper.util.calendar_utils as calendar_utils
import vesper.util.preferences as prefs


_UNVISITED_DAY_COLOR = (0, 0, 1, .2)
_VISITED_DAY_COLOR = (.5, .5, .5, .2)
_HIGHLIGHTED_DAY_COLOR = (0, 1, 0, .2)


class ClipCountMonthCalendar(QFrame):
    
    
    @staticmethod
    def get_size_hint():
        # We fix the size of month calendars since we don't want them
        # to expand or contract as the available space changes within
        # the UI. We may need to change the size, however, if the font
        # or font size used in the calendar changes. Hence we support
        # width and height preferences.
        width = prefs.get('monthCalendar.width', 300)
        height = prefs.get('monthCalendar.height', 250)
        return QSize(width, height)
    

    def __init__(self, parent, archive):
        
        super(ClipCountMonthCalendar, self).__init__(parent)
        
        self._archive = archive
        
        self._station_name = None
        self._detector_name = None
        self._clip_class_name = None
        self._year = None
        self._month = None
        
        self._notifier = Notifier()

        self._figure = Figure()
        self._figure.set_facecolor(self._get_figure_face_color())
       
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setParent(self)

        self._axes = self._figure.add_subplot(111)
#        self._axes = self._figure.add_axes([.05, .05, .9, .9])
             
        connect = self._canvas.mpl_connect
        connect('motion_notify_event', self._on_motion)
        connect('figure_leave_event', self._on_figure_leave)
        connect('axes_leave_event', self._on_axes_leave)
        connect('pick_event', self._on_pick)
        
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


    def _on_motion(self, e):
        
        axes = e.inaxes
        
        if axes is not None:
            
            index = self._get_path_index(e)
                
            if self._mouse_index != index:
                self._update_day_colors(index)
#                 if index is not None:
#                     print('motion', index + 1, axes.get_title())
        
        
    def _get_path_index(self, e):
        
        _, props = self._path_collection.contains(e)
        indices = props['ind']
        
        if len(indices) == 0:
            return None
            
        elif len(indices) == 1:
            return indices[0]
        
        else:
            x_deltas = self._x[indices] - e.xdata
            y_deltas = self._y[indices] - e.ydata
            return indices[np.argmin(x_deltas ** 2 + y_deltas ** 2)]

    
    def _update_day_colors(self, index):
          
        colors = [
            _VISITED_DAY_COLOR if self._visited[i] else _UNVISITED_DAY_COLOR
            for i in xrange(len(self._visited))]
        
        if index is not None:
            colors[index] = _HIGHLIGHTED_DAY_COLOR
        
        self._path_collection.set_facecolors(colors)
        
        self._canvas.draw()
        
        self._mouse_index = index
        
        
    def _on_figure_leave(self, e):
        self._update_day_colors(None)
#        print('_on_figure_leave')
        
        
    def _on_axes_leave(self, e):
        self._update_day_colors(None)
#        print('leave', e.inaxes.get_title())
        
        
    def _on_pick(self, e):
        # We must test the type of mouse event that resulted in this
        # pick event, since (for some reason) pick events result from
        # both button press events and scroll events. We also only
        # respond to events from the primary mouse button.
        e = e.mouseevent
        if e.name == 'button_press_event' and e.button == 1:
            index = self._get_path_index(e)
            self._visited[index] = True
            date = datetime.date(self.year, self.month, index + 1)
            self._notifier.notify_listeners(date)
            self._pick_enabled = False
        
        
    def _get_figure_face_color(self):
        
        """
        Gets a Matplotlib figure face color that will match the
        Qt palette window color.
        """
        
        c = self.palette().window().color()
        color = (c.red(), c.green(), c.blue(), c.alpha())
        
        if platform.system() == 'Darwin':
            # running on Mac OS X
            
            # The color we get from the palette seems to be a little
            # darker than the actual window color (at least for Mac OS X),
            # so we apply the following empirically-derived "fix".
            # TODO: Figure out why the colors don't match and report
            # a bug somewhere (probably to either Matplotlib or PyQt4).
            return tuple(min(c / 249.5, 1) for c in color)
        
        else:
            # not running on Mac OS X
            
            return tuple(c / 255. for c in color)
 
     
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
        
        axes = self._axes
        axes.cla()
        
        if self._station_name is not None:
            
            (first_day_offset, num_days) = calendar.monthrange(year, month)
            
            start_date = datetime.date(year, month, 1)
            end_date = datetime.date(year, month, num_days)
            
            counts = self._archive.get_clip_counts(
                self.station_name, self.detector_name, start_date, end_date,
                self.clip_class_name)
            
            start_offset = (first_day_offset + 1) % 7
            end_offset = start_offset + num_days
            
            day_nums = np.tile(np.arange(7, dtype='float'), 6)
            x = day_nums[start_offset:end_offset]
            
            week_nums = np.hstack([np.repeat(i, 7) for i in xrange(6)])
            y = week_nums[start_offset:end_offset]
            
            sizes = np.zeros(num_days)
            for i in xrange(num_days):
                try:
                    count = counts[datetime.date(year, month, i + 1)]
                except KeyError:
                    sizes[i] = 0
                else:
                    sizes[i] = 500 + count
                
            self._path_collection = axes.scatter(
                x, y, s=sizes, c=_UNVISITED_DAY_COLOR, alpha=.2,
                clip_on=False, pickradius=0, picker=True)
            self._x = x
            self._y = y
            self._mouse_index = None
            self._visited = [False] * num_days
            
            for i in xrange(num_days):
                axes.text(x[i], y[i], str(i + 1), ha='center', va='center')
            
            axes.set_xlim(-.5, 6.5)
            axes.set_ylim(-.5, 5.5)
            axes.invert_yaxis()
                   
            axes.xaxis.set_visible(False)
            axes.yaxis.set_visible(False)
            
            axes.set_frame_on(False)

            axes.set_title(calendar_utils.get_year_month_string(year, month))
            
        self._canvas.draw()


    def sizeHint(self):
        return self.get_size_hint()
    
    
    def resizeEvent(self, event):
        r = self.contentsRect()
        self._canvas.setGeometry(r.x(), r.y(), r.width(), r.height())
        
        
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
        
        
    def remove_listener(self, listener):
        self._notifier.remove_listener(listener)
        
        
    def clear_listeners(self):
        self._notifier.clear_listeners()
