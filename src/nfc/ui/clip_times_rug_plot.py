from __future__ import print_function

import datetime
import math

import matplotlib as mpl
mpl.rcParams['backend.qt4'] = 'PyQt4'
    
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from PyQt4.QtGui import QSizePolicy
import numpy as np
import pytz


_BACKGROUND_COLOR = (0, 0, 0, 0)
_LINE_COLOR = (0, 0, 0)
_CURRENT_PAGE_COLOR = (.6, .6, 1)
_MOUSE_PAGE_COLOR = (.5, 1, .5)
_MAX_PLOT_WIDTH = 800
_PLOT_HEIGHT = 50
_START_TIME = 18         # hours after night date midnight
_END_TIME = 30           # hours after night date midnight
_PADDING = .2            # hours
_LINE_START_Y = .2
_LINE_END_Y = .8


# TODO: Perhaps it would make most sense to subclass `Figure`?


class ClipTimesRugPlot(object):
    
    
    def __init__(self, parent, observer):
        
        super(ClipTimesRugPlot, self).__init__()
        
        self._observer = observer
        
        self._figure = Figure()
        self._figure.patch.set_facecolor(_BACKGROUND_COLOR)
        
        self._canvas = Canvas(self._figure)
        self._canvas.setParent(parent)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._canvas.setMaximumWidth(_MAX_PLOT_WIDTH)
        self._canvas.setFixedHeight(_PLOT_HEIGHT)
        
        connect = self._canvas.mpl_connect
        connect('axes_enter_event', self._on_axes_enter)
        connect('axes_leave_event', self._on_axes_leave)
        connect('motion_notify_event', self._on_motion)
        connect('button_press_event', self._on_button_press)
        
        # We inset the axes a little from the figure edges since we have
        # found that if we don't the line at the right edge of the plot
        # may be clipped.
        self._axes = self._figure.add_axes([.025, .5, .95, .475])
        
        # Hide Y axis since there's nothing to label.
        self._axes.yaxis.set_visible(False)
        
        self._clip_times = []
        self._clip_lines = None
        
        self._current_page_num = None
        self._current_page_lines = None
        
        self._mouse_page_num = None
        self._mouse_page_lines = None
        
        self._draw()


    def _on_axes_enter(self, event):
        self._on_mouse_event(event, 'axes enter')
        
        
    def _on_axes_leave(self, event):
        self._on_mouse_event(event, 'axes leave')
        
        
    def _on_motion(self, event):
        self._on_mouse_event(event, 'motion')
        
        
    def _on_mouse_event(self, event, name):
        self.mouse_page_num = self._get_mouse_page_num(event)
        
        
    def _get_mouse_page_num(self, event):
        
        if hasattr(event, 'xdata') and \
                event.xdata is not None and \
                event.ydata >= _LINE_START_Y and \
                event.ydata <= _LINE_END_Y:
                # mouse over clips area
            
            return _find_page_num(event.xdata, self._page_boundary_times)
                
        else:
            # mouse not over clips area
            
            return None


    def _on_button_press(self, event):
        page_num = self._get_mouse_page_num(event)
        if page_num is not None:
            self._observer(page_num)
        
        
    @property
    def canvas(self):
        return self._canvas
    
    
    def set_clips(self, clips, page_start_indices):
        
        clip_times = _get_clip_times(clips)
        num_clips = len(clip_times)
        
        page_indices = page_start_indices
        num_pages = len(page_indices)

        page_times = [clip_times[page_indices[i]] for i in xrange(num_pages)]
        
        # Append last page end to page boundary arrays.
        if num_clips > 0:
            page_indices.append(num_clips)
            page_times.append(clip_times[-1])
        
        self._clip_times = clip_times
        self._page_boundary_indices = page_indices
        self._page_boundary_times = page_times
        
        self._clear_current_page()
        self._clear_mouse_page()
        
        self._draw()
        
        
    def _clear_current_page(self):
        self._current_page_num = None
        if self._current_page_lines is not None:
            self._axes.collections.remove(self._current_page_lines)
            self._current_page_lines = None
            
            
    def _clear_mouse_page(self):
        self._mouse_page_num = None
        if self._mouse_page_lines is not None:
            self._axes.collections.remove(self._mouse_page_lines)
            self._mouse_page_lines = None
            
        
    @property
    def current_page_num(self):
        return self._current_page_num
    
    
    @current_page_num.setter
    def current_page_num(self, page_num):
        if page_num != self._current_page_num:
            self._current_page_lines = self._update_page_highlighting(
                self._current_page_lines, page_num, _CURRENT_PAGE_COLOR, 2)
            self._current_page_num = page_num
            self._canvas.draw()
            
            
    @property
    def mouse_page_num(self):
        return self._mouse_page_num
    
    
    @mouse_page_num.setter
    def mouse_page_num(self, page_num):
        if page_num != self._mouse_page_num:
            self._mouse_page_lines = self._update_page_highlighting(
                self._mouse_page_lines, page_num, _MOUSE_PAGE_COLOR, 1)
            self._mouse_page_num = page_num
            self._canvas.draw()
            
            
    def _update_page_highlighting(
            self, old_lines, new_page_num, color, z_order_offset):
        
        if old_lines is not None:
            self._axes.collections.remove(old_lines)
             
        if new_page_num is not None:
            
            i = new_page_num
            start, end = self._page_boundary_indices[i:i + 2]
            times = self._clip_times[start:end]
            
            new_lines = self._axes.vlines(
                times, _LINE_START_Y, _LINE_END_Y, colors=color)
            
            z_order = self._clip_lines.get_zorder() + z_order_offset
            new_lines.set_zorder(z_order)
            
        else:
            # no page to highlight
            
            new_lines = None
            
        return new_lines

        
    def _draw(self):
        
        axes = self._axes
        
        # Clear axes since we will redraw the entire plot.
        axes.cla()
        self._clip_lines = None
        self._current_page_lines = None
        self._mouse_page_lines = None
        
        # Configure X axis.
        axes.set_xlim([_START_TIME - _PADDING, _END_TIME + _PADDING])
        tick_xs, tick_labels = _get_tick_data(_START_TIME, _END_TIME)
        axes.set_xticks(tick_xs)
        axes.set_xticklabels(tick_labels)
        axes.get_xaxis().set_tick_params(direction='out', top='off')
        
        # Configure Y axis.
        axes.set_ylim([0, 1])
        
        # Make plot background transparent.
        axes.set_axis_bgcolor(_BACKGROUND_COLOR)
            
        if len(self._clip_times) != 0:
             
            self._clip_lines = axes.vlines(
                self._clip_times, _LINE_START_Y, _LINE_END_Y,
                colors=_LINE_COLOR)
             
        self._canvas.draw()
            
            
def _get_clip_times(clips):
    
    """
    Gets the times of the specified clips in hours past midnight of
    the night date of the first clip.
    
    We assume that the clips are in order of increasing time.
    """
    
    if len(clips) == 0:
        times = []
        
    else:
        # have at least one clip
        
        # Get local midnight of first clip night date as a UTC time.
        #
        # Note that it's important to use `clip.night` in the following
        # rather than the date of `clip.time`, since the date of the
        # latter can be one day later than what we want.
        #
        # Note also that contrary to what one might expect the following
        # would not work:
        #
        #     local_midnight = datetime.datetime(
        #         date.year, date.month, date.day, tzinfo=time_zone)
        #
        # since (as of 2014-12-04, at least) pytz time zones cannot be
        # used as arguments to the standard datetime constructor. See
        # the "Example & Usage" section of http://pytz.sourceforge.net
        # for more information.
        clip = clips[0]
        date = clip.night
        naive_midnight = datetime.datetime(date.year, date.month, date.day)
        time_zone = clip.station.time_zone
        local_midnight = time_zone.localize(naive_midnight)
        ref_time = local_midnight.astimezone(pytz.utc)

        times = [(c.time - ref_time).total_seconds() / 3600 for c in clips]
        
    return np.array(times)


def _find_page_num(time, page_boundary_times):
    
    times = page_boundary_times
    
    if len(times) == 0:
        # no pages
        
        return None
    
    else:
        # one or more pages
        
        num_pages = len(times) - 1
        
        # Find page number of time `time`, where page numbers begin
        # at zero. The time interval for page `i` is:
        #
        #     [times[i], times[i + 1])
        #
        # except that the last page is closed on the right.
        i = np.searchsorted(times, time, side='right') - 1
        if i == num_pages and time == times[-1]:
            i -= 1
            
        return i if i >= 0 and i < num_pages else None


def _get_tick_data(start_time, end_time):
    
    start_hour = int(math.ceil(start_time))
    end_hour = int(math.floor(end_time))
    
    xs = range(start_hour, end_hour + 1)
    labels = [_get_tick_label(x) for x in xs]
    
    return (xs, labels)
    
    
def _get_tick_label(x):
    return str(x % 24) if x % 2 == 0 else ''
