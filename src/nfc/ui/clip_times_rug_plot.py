from __future__ import print_function

import datetime

import matplotlib as mpl
mpl.rcParams['backend.qt4'] = 'PyQt4'
    
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
from PyQt4.QtGui import QSizePolicy
import numpy as np
import pytz


_BACKGROUND_COLOR = (.7, .7, .7)
_LINE_COLOR = (0, 0, 0)
_HIGHLIGHT_COLOR = (.5, 1, .5)
_MAX_PLOT_WIDTH = 800
_PLOT_HEIGHT = 25
_START_TIME = 18         # hours after night date midnight
_END_TIME = 30           # hours after night date midnight
_PADDING = .2            # hours
_LINE_START_Y = .3
_LINE_END_Y = .8


# TODO: Perhaps it would make most sense to subclass `Figure`?


class ClipTimesRugPlot(object):
    
    
    def __init__(self, parent):
        
        super(ClipTimesRugPlot, self).__init__()
        
        self._figure = Figure()
        self._figure.patch.set_facecolor(_BACKGROUND_COLOR)
        
        self._canvas = Canvas(self._figure)
        self._canvas.setParent(parent)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._canvas.setMaximumWidth(_MAX_PLOT_WIDTH)
        self._canvas.setFixedHeight(_PLOT_HEIGHT)
        
        self._axes = self._figure.add_axes([0, 0, 1, 1])
        self._axes.set_frame_on(False)
        self._axes.xaxis.set_visible(True)
        self._axes.yaxis.set_visible(False)
            
        self._clips = []
        self._clip_times = []
        self._clip_lines = None
        
        self._first_highlighted_clip_num = None
        self._num_highlighted_clips = 0
        self._highlighting_lines = None
        
        self._draw()


    @property
    def canvas(self):
        return self._canvas
    
    
    @property
    def clips(self):
        return self._clips
    
    
    @clips.setter
    def clips(self, clips):
        self._clips = clips
        self._clip_times = _get_clip_times(self._clips)
        self._first_highlighted_clip_num = None
        self._num_highlighted_clips = 0
        self._draw()
        
        
    def highlight_clips(self, first_clip_num, num_clips):
        self._first_highlighted_clip_num = first_clip_num
        self._num_highlighted_clips = num_clips
        self._update_highlighting()
        self._canvas.draw()
            
            
    def _draw(self):
        
        axes = self._axes
        
        axes.cla()
        self._clip_lines = None
        self._highlighting_lines = None
        
        if len(self._clips) != 0:
            
            axes.set_xlim([_START_TIME - _PADDING, _END_TIME + _PADDING])
            axes.set_ylim([0, 1])
            
            self._clip_lines = axes.vlines(
                self._clip_times, _LINE_START_Y, _LINE_END_Y,
                colors=_LINE_COLOR)
            
            self._update_highlighting()
            
        self._canvas.draw()
            
            
    def _update_highlighting(self):
        
        if self._highlighting_lines is not None:
            self._axes.collections.remove(self._highlighting_lines)
            
        n = self._num_highlighted_clips
        
        if self._num_highlighted_clips != 0:
            
            i = self._first_highlighted_clip_num
            times = self._clip_times[i:i + n]
            
            self._highlighting_lines = self._axes.vlines(
                times, _LINE_START_Y, _LINE_END_Y, colors=_HIGHLIGHT_COLOR)
            
            # Set highlighting lines z order to ensure that they are
            # drawn on top of other lines.
            z_order = self._clip_lines.get_zorder() + 1
            self._highlighting_lines.set_zorder(z_order)


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
